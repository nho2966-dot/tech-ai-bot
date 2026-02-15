import os
import sqlite3
import hashlib
import time
import random
import re
import logging
import yaml
from datetime import datetime
import tweepy
import feedparser
import requests
from dotenv import load_dotenv
from openai import OpenAI

# دعم مكتبة Google GenAI لعام 2026
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

load_dotenv()

class SovereignBot:
    def __init__(self, config_path="utils/config.yaml"):
        self.cfg = None
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.cfg = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            exit(1)

        self._init_logging()
        self._init_db()

        # تهيئة محرك ذكاء جوجل
        self.google_client = None
        google_key = os.getenv(self.cfg['api_keys'].get('google', 'GOOGLE_API_KEY'))
        if google_key and genai is not None:
            try:
                self.google_client = genai.Client(api_key=google_key)
                self.logger.info("✅ Google GenAI Initialized")
            except Exception as e:
                self.logger.error(f"⚠️ Google GenAI Init Failed: {e}")

        # تهيئة الاتصال بمنصة X
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True
            )
            me = self.x.get_me(user_auth=True)
            self.bot_id = str(me.data.id) if me and me.data else None
            self.logger.info(f"🛡️ Connected to X | ID: {self.bot_id}")
        except Exception as e:
            self.logger.critical(f"🛑 X API Failed: {e}")
            exit(1)

    def _init_logging(self):
        l_cfg = self.cfg.get('logging', {})
        logging.basicConfig(
            level=getattr(logging, l_cfg.get('level', 'INFO')),
            format=l_cfg.get('format', '%(asctime)s | %(levelname)s | %(message)s'),
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(l_cfg.get('name', 'SovereignBot'))

    def _init_db(self):
        db_path = self.cfg['bot']['database_path']
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        with sqlite3.connect(db_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()

    def _brain(self, content: str = "", mode: str = "POST") -> str:
        sys_rules = self.cfg['prompts']['system_core']
        prompt_tmpl = self.cfg['prompts']['modes'].get(mode, "{content}")
        user_prompt = prompt_tmpl.format(content=content)
        rtl = self.cfg['bot']['rtl']

        for model_cfg in self.cfg['models']['priority']:
            api_key = os.getenv(model_cfg['env_key'])
            if not api_key: continue
            try:
                text = ""
                if model_cfg['type'] == "openai":
                    client = OpenAI(api_key=api_key, base_url=model_cfg.get('base_url'))
                    res = client.chat.completions.create(
                        model=model_cfg['model'],
                        messages=[{"role": "system", "content": sys_rules}, {"role": "user", "content": user_prompt}],
                        temperature=model_cfg.get('temperature', 0.7),
                        max_tokens=model_cfg.get('max_tokens', 250)
                    )
                    text = res.choices[0].message.content.strip()
                elif model_cfg['type'] == "google" and self.google_client:
                    res = self.google_client.models.generate_content(
                        model=model_cfg['model'],
                        config=types.GenerateContentConfig(
                            system_instruction=sys_rules,
                            temperature=model_cfg.get('temperature', 0.7),
                            max_output_tokens=model_cfg.get('max_output_tokens', 250)
                        ),
                        contents=[{"role": "user", "parts": [{"text": user_prompt}]}]
                    )
                    text = res.candidates[0].content.parts[0].text.strip()
                
                if not text: continue
                text = re.sub(r'<(thinking|reasoning|think)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
                text = text[:230].rstrip(' .,!؟')
                return f"{rtl['embed']}{rtl['mark']}{text}{self.cfg['features']['hashtags']['default']}{rtl['pop']}"
            except Exception as e:
                self.logger.warning(f"🔄 Bypass {model_cfg['name']}: {str(e)[:50]}")
                continue
        return f"{rtl['embed']}{rtl['mark']}الوعي التقني هو القوة في عصر الثورة الرابعة.{rtl['pop']}"

    def fetch(self):
        headers = {'User-Agent': self.cfg['bot']['user_agent']}
        feeds = self.cfg.get('sources', {}).get('rss_feeds', [])
        for feed_cfg in feeds:
            url = feed_cfg.get('url') if isinstance(feed_cfg, dict) else feed_cfg
            try:
                r = requests.get(url, headers=headers, timeout=15)
                feed = feedparser.parse(r.content)
                max_items = feed_cfg.get('max_items', 5) if isinstance(feed_cfg, dict) else 5
                for e in feed.entries[:max_items]:
                    title = (e.get('title') or "").strip()
                    if not title: continue
                    h = hashlib.sha256(title.encode('utf-8')).hexdigest()
                    with sqlite3.connect(self.cfg['bot']['database_path']) as conn:
                        conn.execute("INSERT OR IGNORE INTO queue (h, title) VALUES (?,?)", (h, title))
                        conn.commit()
                self.logger.info(f"📡 RSS Done: {url}")
            except Exception as e:
                self.logger.error(f"❌ RSS Failed ({url}): {e}")

    def handle_interactions(self):
        last_id = self._get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id, max_results=5)
            if not mentions or not mentions.data: return
            new_last = last_id
            for m in mentions.data:
                new_last = max(new_last, str(m.id))
                with sqlite3.connect(self.cfg['bot']['database_path']) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(m.id),)).fetchone(): continue
                    reply = self._brain(m.text, "REPLY")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=m.id)
                        c.execute("INSERT INTO replies (tweet_id, created_at) VALUES (?,?)", (str(m.id), datetime.now().isoformat()))
                        c.commit()
                        time.sleep(2) # فاصل بسيط بين الردود
            self._update_meta("last_mention_id", new_last)
        except: pass

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))
        if count >= self.cfg['bot']['daily_tweet_limit']:
            self.logger.info("📅 Daily limit reached.")
            return
        
        content, queue_hash = None, None
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            if random.random() < self.cfg['features']['ai_tools_posts']['probability']:
                topic = random.choice(self.cfg['features']['ai_tools_posts']['topics'])
                content = self._brain(topic, "TOOL_POST")
            else:
                row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
                if row:
                    content = self._brain(row[1], "POST")
                    queue_hash = row[0]

        if content:
            try:
                self.logger.info(f"📝 Preparing to post: {content[:50]}...")
                poll_cfg = self.cfg['twitter'].get('poll', {})
                if random.random() < poll_cfg.get('enabled_probability', 0):
                    self.x.create_tweet(
                        text=content,
                        poll={
                            "options": poll_cfg.get('default_options', ["نعم", "لا"]),
                            "duration_minutes": poll_cfg.get('duration_minutes', 1440)
                        }
                    )
                else:
                    self.x.create_tweet(text=content)
                
                if queue_hash:
                    with sqlite3.connect(self.cfg['bot']['database_path']) as c2:
                        c2.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (queue_hash,))
                        c2.commit()
                self._update_meta(f"daily_count_{today}", str(count + 1))
                self.logger.info("🚀 TWEET PUBLISHED SUCCESSFULLY!")
            except Exception as e:
                self.logger.error(f"❌ Dispatch Error: {e}")

    def _get_meta(self, key, default="0"):
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key, value):
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            c.commit()

    def run(self):
        self.logger.info("⚙️ Starting Sovereign Cycle v550...")
        # 1. Fetch data (Internal, no X API cost)
        self.fetch()
        
        # 2. Priority: Dispatch Tweet
        self.dispatch()
        
        # 3. Handle Interactions (After delay to avoid rate limits)
        time.sleep(10) 
        self.handle_interactions()
        self.logger.info("🏁 Cycle Completed.")

if __name__ == "__main__":
    bot = SovereignBot("utils/config.yaml")
    bot.run()
