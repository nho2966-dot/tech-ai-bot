import os, sqlite3, hashlib, time, random, re, logging
from datetime import datetime
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- الإعدادات الفنية النخبوية ---
CONFIG = {
    "DB": "sovereign_v550.db",
    "MAX_REPLIES": 2,
    "DAILY_MAX_TWEETS": 10,
    "REPLY_DELAY": 60,
    "MODELS": [
        {"name": "Grok", "base": "https://api.x.ai/v1", "key": os.getenv("XAI_API_KEY"), "model": "grok-2"},
        {"name": "Qwen", "base": "https://openrouter.ai/api/v1", "key": os.getenv("OPENROUTER_API_KEY"), "model": "qwen/qwen-2.5-72b-instruct"},
        {"name": "Gemini-Free", "base": "https://openrouter.ai/api/v1", "key": os.getenv("OPENROUTER_API_KEY"), "model": "google/gemini-2.0-flash-exp:free"}
    ]
}

# رموز التحكم في اتجاه النص (RTL) للغة العربية الرصينة
RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SovereignTripleAI")

class SovereignBot:
    def __init__(self):
        self._init_db()
        self.sources = [
            "https://www.jook.me/rss/technology", # المصدر النخبوي الأول
            "https://www.arabnews.com/rss/technology",
            "https://www.zawya.com/en/rss/technology"
        ]
        
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
            logger.info(f"تم تسجيل الدخول - المعرف: {self.bot_id}")
        except Exception as e:
            logger.critical(f"فشل الاتصال بـ X: {e}"); exit(0)

    def _init_db(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()

    def _brain(self, content="", mode="POST"):
        sys_rules = (
            "أنت مستشار تقني خليجي نخبوي. لغتك رصينة وقورة. "
            "تركيزك: السيادة الرقمية للفرد، الثورة الصناعية الرابعة، و(HUMAIN OS). "
            "استخدم أسلوب 'جوك' الفلسفي لتحويل الخبر إلى رؤية سيادية."
        )
        prompts = {
            "POST": f"حلل بأسلوب 'جوك' النخبوي أثر هذا الخبر على سيادة الفرد: {content}",
            "REPLY": f"رد بوقار نخبوي يثير تساؤلاً فلسفياً: {content}"
        }

        for m_cfg in CONFIG["MODELS"]:
            if not m_cfg["key"]: continue
            try:
                client = OpenAI(api_key=m_cfg["key"], base_url=m_cfg["base"])
                res = client.chat.completions.create(
                    model=m_cfg["model"],
                    messages=[{"role": "system", "content": sys_rules}, {"role": "user", "content": prompts[mode]}],
                    timeout=25
                )
                logger.info(f"تم التوليد عبر {m_cfg['name']}")
                return f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"
            except Exception as e:
                logger.warning(f"المحرك {m_cfg['name']} غير متاح: {e}")
                continue
        return ""

    def fetch(self):
        logger.info("جاري استقاء المعرفة من جوك والمصادر النخبوية...")
        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                count = 5 if "jook" in src else 2
                for e in feed.entries[:count]:
                    title = e.title.strip()
                    h = hashlib.sha256(title.encode()).hexdigest()
                    with sqlite3.connect(CONFIG["DB"]) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title) VALUES (?,?)", (h, title))
                        c.commit()
            except: continue

    def handle_interactions(self):
        last_id = self._get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id, max_results=5)
            if not mentions or not mentions.data: return
            new_last_id = last_id
            for m in mentions.data:
                new_last_id = max(int(new_last_id), m.id)
                with sqlite3.connect(CONFIG["DB"]) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(m.id),)).fetchone(): continue
                    reply = self._brain(m.text, mode="REPLY")
                    if reply:
                        self.x.create_tweet(text=reply[:280], in_reply_to_tweet_id=m.id)
                        c.execute("INSERT INTO replies VALUES (?,?)", (str(m.id), datetime.now().isoformat()))
                        c.commit()
                        time.sleep(CONFIG["REPLY_DELAY"])
            self._update_meta("last_mention_id", str(new_last_id))
        except Exception as e: logger.warning(f"تخطي المنشنز: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))
        if count >= CONFIG["DAILY_MAX_TWEETS"]: return
        try:
            with sqlite3.connect(CONFIG["DB"]) as c:
                row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' LIMIT 1").fetchone()
                if row:
                    content = self._brain(row[1], "POST")
                    if content:
                        self.x.create_tweet(text=content[:280])
                        c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row[0],))
                        c.commit()
                        self._update_meta(f"daily_count_{today}", str(count + 1))
        except Exception as e: logger.warning(f"تخطي النشر: {e}")

    def _get_meta(self, key, default):
        with sqlite3.connect(CONFIG["DB"]) as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key, value):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            c.commit()

    def run(self):
        self.fetch()
        self.handle_interactions()
        self.dispatch()

if __name__ == "__main__":
    SovereignBot().run()
