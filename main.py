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
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class SovereignBot:
    def __init__(self, config_path="utils/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)

        self._init_logging()
        self._init_db()

        # تهيئة OpenAI - يفضل استخدام gpt-4o في ملف config
        self.openai_clients = []
        for model_cfg in self.cfg['models']['priority']:
            api_key = os.getenv(model_cfg['env_key'])
            if api_key and model_cfg['type'] == "openai":
                self.openai_clients.append((model_cfg, OpenAI(api_key=api_key)))

        # تهيئة X API
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
            self.logger.info(f"🛡️ Sovereign Bot Active | ID: {self.bot_id}")
        except Exception as e:
            self.logger.critical(f"🛑 X API Connection Failed: {e}")
            exit(1)

        self.monitored_accounts = self.cfg.get('monitored_accounts', [])

    def _init_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('SovereignBot')

    def _init_db(self):
        db_path = self.cfg['bot']['database_path']
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        # إضافة timeout لمنع خطأ database is locked
        with sqlite3.connect(db_path, timeout=30) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, link TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()

    def is_sleep_time(self):
        current_hour = datetime.now().hour
        start = self.cfg['bot'].get('sleep_start', 2)
        end = self.cfg['bot'].get('sleep_end', 8)
        if start < end:
            return start <= current_hour < end
        return current_hour >= start or current_hour < end

    def _scrape_article(self, url):
        try:
            headers = {'User-Agent': self.cfg['bot']['user_agent']}
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.content, 'html.parser')
            paragraphs = soup.find_all('p')
            return " ".join([p.get_text() for p in paragraphs[:8]])[:1500]
        except: return ""

    def _brain(self, content: str, mode: str):
        sys_rules = self.cfg['prompts']['system_core']
        prompt_tmpl = self.cfg['prompts']['modes'].get(mode, "{content}")
        user_prompt = prompt_tmpl.format(content=content)

        for model_cfg, client in self.openai_clients:
            try:
                res = client.chat.completions.create(
                    model=model_cfg['model'],
                    messages=[{"role": "system", "content": sys_rules},
                              {"role": "user", "content": user_prompt}],
                    temperature=0.7,
                    max_tokens=450
                )
                text = res.choices[0].message.content.strip()
                limit = 400 if mode in ["POST_DEEP", "THREAD_START"] else 280
                return text[:limit].rstrip(' .,!؟')
            except Exception as e:
                self.logger.warning(f"🔄 AI Error ({model_cfg['model']}): {e}")
        return "الوعي بالسيادة التقنية هو ضرورة المرحلة."

    def dispatch(self):
        if self.is_sleep_time(): return

        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))
        last_ts = int(self._get_meta(f"last_post_ts_{today}", "0"))

        if count >= self.cfg['bot'].get('daily_tweet_limit', 40): return
        if time.time() - last_ts < 7200: return 

        db_path = self.cfg['bot']['database_path']
        with sqlite3.connect(db_path, timeout=30) as c:
            row = c.execute("SELECT h, title, link FROM queue WHERE status='PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
            if row:
                article = self._scrape_article(row[2])
                dice = random.random()
                mode = "THREAD_START" if dice < 0.2 else ("POST_DEEP" if len(article) > 700 else "POST_FAST")
                
                content = self._brain(f"Title: {row[1]}\nContext: {article}", mode)
                if content:
                    try:
                        time.sleep(random.uniform(30, 60))
                        self.x.create_tweet(text=content)
                        c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row[0],))
                        c.commit()
                        self._update_meta(f"daily_count_{today}", str(count + 1))
                        self._update_meta(f"last_post_ts_{today}", str(int(time.time())))
                        self.logger.info(f"🚀 Published: {mode}")
                    except Exception as e:
                        self.logger.error(f"❌ Dispatch Error: {e}")

    def handle_replies(self):
        if self.is_sleep_time(): return
        
        today = datetime.now().date().isoformat()
        r_count = int(self._get_meta(f"replies_today_{today}", "0"))
        if r_count >= self.cfg['bot'].get('daily_reply_limit', 20): return

        db_path = self.cfg['bot']['database_path']
        for acc in self.monitored_accounts:
            try:
                # محاولة جلب التغريدات مع معالجة الأخطاء
                response = self.x.get_users_tweets(id=acc, max_results=5)
                tweets = response.data or []
                for t in tweets:
                    with sqlite3.connect(db_path, timeout=30) as c:
                        if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(t.id),)).fetchone(): continue
                        
                        reply_content = self._brain(t.text, "REPLY")
                        time.sleep(random.uniform(40, 90))
                        self.x.create_tweet(text=reply_content, in_reply_to_tweet_id=t.id)
                        
                        c.execute("INSERT INTO replies (tweet_id, created_at) VALUES (?,?)", (str(t.id), datetime.now().isoformat()))
                        c.commit()
                        self._update_meta(f"replies_today_{today}", str(r_count + 1))
                        self.logger.info(f"💬 Strategic Reply sent to: {acc}")
                        return # تنفيذ رد واحد فقط في الدورة لحماية الحساب
            except Exception as e:
                self.logger.warning(f"⚠️ Reply cycle skipped for {acc}: {e}")
                continue

    def _get_meta(self, key, default="0"):
        with sqlite3.connect(self.cfg['bot']['database_path'], timeout=30) as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key, value):
        with sqlite3.connect(self.cfg['bot']['database_path'], timeout=30) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            c.commit()

    def run(self):
        self.logger.info("⚙️ Sovereign Cycle Initiated...")
        # جلب الروابط وتحديث القائمة
        try:
            feed_url = self.cfg['sources']['rss_feeds'][0]['url']
            feed = feedparser.parse(feed_url)
            with sqlite3.connect(self.cfg['bot']['database_path'], timeout=30) as c:
                for e in feed.entries[:10]:
                    h = hashlib.sha256(e.title.encode()).hexdigest()
                    c.execute("INSERT OR IGNORE INTO queue (h, title, link) VALUES (?,?,?)", (h, e.title, e.link))
                c.commit()
        except Exception as e:
            self.logger.error(f"📡 RSS Fetch Error: {e}")

        self.dispatch()
        self.handle_replies()
        self.logger.info("🏁 Cycle Completed.")

if __name__ == "__main__":
    bot = SovereignBot()
    bot.run()
