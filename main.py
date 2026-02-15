import os, sqlite3, hashlib, time, random, re, logging
from datetime import datetime
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# إعدادات التخفي والسيادة التقنية
CONFIG = {
    "DB": "sovereign_v550.db",
    "MAX_REPLIES": 2,
    "DAILY_MAX_TWEETS": 10,
    "REPLY_DELAY": 45
}

RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

# إعداد السجلات (بدون إنشاء ملف مادي لتجنب أخطاء GitHub Git)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SovereignBot")

class SovereignGithubBot:
    def __init__(self):
        self._init_db()
        try:
            self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=False
            )
            me = self.x.get_me()
            self.bot_id = str(me.data.id) if me and me.data else None
            logger.info(f"تم تسجيل الدخول - المعرف: {self.bot_id}")
        except Exception as e:
            logger.critical(f"فشل الاتصال: {e}"); exit(0)

    def _init_db(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()

    def _get_meta(self, key, default="0"):
        with sqlite3.connect(CONFIG["DB"]) as c:
            row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def _update_meta(self, key, value):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, str(value)))
            c.commit()

    def handle_interactions(self):
        last_id = int(self._get_meta("last_mention_id", "1"))
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id, max_results=5)
            if not mentions or not mentions.data: return

            new_last_id = last_id
            for m in mentions.data:
                new_last_id = max(new_last_id, m.id)
                with sqlite3.connect(CONFIG["DB"]) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(m.id),)).fetchone(): continue
                    
                    res = self.ai.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=[{"role": "system", "content": "مستشار تقني خليجي رصين يركز على السيادة الرقمية."}, 
                                  {"role": "user", "content": f"رد بوقار نخبوي: {m.text}"}],
                        timeout=25
                    )
                    reply = f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"
                    self.x.create_tweet(text=reply[:280], in_reply_to_tweet_id=m.id)
                    c.execute("INSERT INTO replies VALUES (?,?)", (str(m.id), datetime.now().isoformat()))
                    c.commit()
                    logger.info(f"تم الرد على {m.id}")
                    time.sleep(CONFIG["REPLY_DELAY"])
            self._update_meta("last_mention_id", str(new_last_id))
        except Exception as e: logger.warning(f"تخطى المنشنز: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))
        if count >= CONFIG["DAILY_MAX_TWEETS"]: return

        try:
            if random.random() < 0.6: # نشر خبر مخزن في الطابور
                with sqlite3.connect(CONFIG["DB"]) as c:
                    row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' LIMIT 1").fetchone()
                    if row:
                        self.x.create_tweet(text=f"{RTL_EMBED}{row[1][:270]}{RTL_POP}")
                        c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row[0],))
                        c.commit()
                        self._update_meta(f"daily_count_{today}", str(count + 1))
                        logger.info("تم نشر تغريدة جديدة.")
        except Exception as e: logger.warning(f"تخطى النشر: {e}")

    def run_once(self):
        wait = random.randint(10, 60)
        logger.info(f"بدء الدورة بعد تأخير {wait} ثانية...")
        time.sleep(wait)
        self.handle_interactions()
        self.dispatch()

if __name__ == "__main__":
    SovereignGithubBot().run_once()
