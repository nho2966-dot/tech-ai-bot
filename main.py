import os, sqlite3, hashlib, time, random, re, logging, yaml
from datetime import datetime
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

load_dotenv()

class SovereignBot:
    def __init__(self, config_path="sovereign-config.yaml"):
        # تحميل الإعدادات المركزية
        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)
        
        self._init_logging()
        self._init_db()
        
        # إعداد Google AI Studio إذا وجد المفتاح
        if os.getenv("GOOGLE_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            me = self.x.get_me()
            self.bot_id = str(me.data.id) if me and me.data else None
            self.logger.info(f"النظام السيادي نشط | المعرف: {self.bot_id}")
        except Exception as e:
            self.logger.critical(f"فشل الربط مع X: {e}"); exit(0)

    def _init_logging(self):
        l_cfg = self.cfg['logging']
        logging.basicConfig(level=l_cfg['level'], format=l_cfg['format'])
        self.logger = logging.getLogger(l_cfg['logger_name'])

    def _init_db(self):
        with sqlite3.connect(self.cfg['bot']['database']) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()

    def _brain(self, content="", mode="POST"):
        sys_rules = self.cfg['prompts']['system']
        prompt_tmpl = self.cfg['prompts']['modes'].get(mode, self.cfg['prompts']['modes']['POST'])
        user_prompt = prompt_tmpl.format(content=content)

        for m in self.cfg['models']['priority_order']:
            api_key = os.getenv(m['env_key'])
            if not api_key: continue
            
            try:
                text = ""
                if m['type'] == "openai":
                    client = OpenAI(api_key=api_key, base_url=m['base_url'])
                    res = client.chat.completions.create(
                        model=m['model'],
                        messages=[{"role": "system", "content": sys_rules}, {"role": "user", "content": user_prompt}],
                        temperature=m['temperature'], max_tokens=m['max_tokens'], timeout=m.get('timeout', 40)
                    )
                    text = res.choices[0].message.content.strip()
                
                elif m['type'] == "google":
                    model = genai.GenerativeModel(m['model'])
                    res = model.generate_content(
                        f"{sys_rules}\n\n{user_prompt}",
                        generation_config=genai.types.GenerationConfig(
                            temperature=m['temperature'], 
                            max_output_tokens=m['max_output_tokens']
                        )
                    )
                    text = res.text.strip()

                # تنظيف وتنقية مخرجات التفكير
                text = re.sub(r'<(thinking|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                rtl = self.cfg['bot']['rtl_control_characters']
                final_text = f"{rtl['embed']}{rtl['mark']}{text[:240]}{self.cfg['twitter']['hashtags_default']}{rtl['pop']}"
                self.logger.info(f"تم التوليد بنجاح عبر: {m['name']}")
                return final_text
            except Exception as e:
                self.logger.warning(f"تعذر المحرك {m['name']}: {e}")
                continue
        
        return f"{rtl['embed']}{rtl['mark']}السيادة هي أن تملك قرارك في عالم تملكه البيانات.{rtl['pop']}"

    def fetch(self):
        self.logger.info("جاري استقاء المعرفة من المصادر...")
        headers = {'User-Agent': 'SovereignPeak/2026'}
        for feed_cfg in self.cfg['sources']['rss_feeds']:
            try:
                resp = requests.get(feed_cfg['url'], headers=headers, timeout=15)
                feed = feedparser.parse(resp.content)
                for e in feed.entries[:feed_cfg['max_items']]:
                    h = hashlib.sha256(e.title.encode()).hexdigest()
                    with sqlite3.connect(self.cfg['bot']['database']) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title) VALUES (?,?)", (h, e.title))
                        c.commit()
            except: continue

    def handle_interactions(self):
        last_id = self._get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id, max_results=5)
            if not mentions or not mentions.data: return
            
            for m in mentions.data:
                with sqlite3.connect(self.cfg['bot']['database']) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(m.id),)).fetchone(): continue
                    reply = self._brain(m.text, mode="REPLY")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=m.id)
                        c.execute("INSERT INTO replies VALUES (?,?)", (str(m.id), datetime.now().isoformat()))
                        c.commit()
                        time.sleep(self.cfg['bot']['reply_delay_seconds'])
            self._update_meta("last_mention_id", str(max([men.id for men in mentions.data])))
        except Exception as e: self.logger.error(f"خطأ التفاعل: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))
        if count >= self.cfg['bot']['daily_max_tweets']: return
        
        content, row_id = None, None
        features = self.cfg['features']['ai_tools_posts']
        
        with sqlite3.connect(self.cfg['bot']['database']) as c:
            if random.random() < features['enabled_probability']:
                topic = random.choice(features['topics'])
                content = self._brain(topic, mode="TOOL_POST")
            else:
                row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
                if row:
                    content, row_id = self._brain(row[1], "POST"), row[0]

            if content:
                p_cfg = self.cfg['twitter']['poll']
                if random.random() < p_cfg['enabled_probability']:
                    self.x.create_tweet(text=content, poll={"options": p_cfg['options'], "duration_minutes": p_cfg['duration_minutes']})
                else:
                    self.x.create_tweet(text=content)
                
                if row_id: c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row_id,))
                c.commit()
                self._update_meta(f"daily_count_{today}", str(count + 1))
                time.sleep(random.uniform(self.cfg['twitter']['post_delay_min_seconds'], self.cfg['twitter']['post_delay_max_seconds']))

    def _get_meta(self, key, default):
        with sqlite3.connect(self.cfg['bot']['database']) as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key, value):
        with sqlite3.connect(self.cfg['bot']['database']) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            c.commit()

    def run(self):
        self.fetch(); self.handle_interactions(); self.dispatch()

if __name__ == "__main__":
    SovereignBot().run()
