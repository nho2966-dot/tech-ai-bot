import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # 🚀 توسيع الحدود للحساب المدفوع
        self.ai_calls = 0
        self.MAX_AI_CALLS = 10 

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (user_id TEXT PRIMARY KEY, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        if self.ai_calls >= self.MAX_AI_CALLS: return None
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]
            )
            return r.choices[0].message.content
        except Exception as e:
            logging.error(f"❌ AI Error: {e}")
            return None

    def process_smart_replies(self):
        logging.info("🔍 فحص استفسارات الجمهور (وضع Premium)...")
        query = "(\"كيف أستخدم AI\" OR \"أفضل أداة ذكاء\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=20, user_auth=True)
            if not tweets or not tweets.data: return

            replies_count = 0
            for t in tweets.data:
                if self.ai_calls >= self.MAX_AI_CALLS or replies_count >= 5: break
                
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM replies WHERE user_id=?", (str(t.author_id),)).fetchone(): continue

                reply_txt = self._safe_ai_call("أنت خبير تقني ودود ومختصر.", t.text)
                if reply_txt:
                    self.x.create_tweet(text=reply_txt[:280], in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO replies VALUES (?, ?)", (str(t.author_id), datetime.now().isoformat()))
                        conn.commit()
                    replies_count += 1
                    logging.info(f"✅ تم الرد رقم {replies_count}")
                    time.sleep(2)
        except Exception as e:
            logging.error(f"❌ خطأ الردود: {e}")

    def execute_publishing(self):
        if self.ai_calls >= self.MAX_AI_CALLS: return
        logging.info("🌍 نشر أخبار التقنية 4.0...")
        feed = feedparser.parse("https://www.theverge.com/rss/index.xml")
        
        for e in feed.entries[:5]:
            h = hashlib.sha256(e.title.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

            content = self._safe_ai_call("أنت خبير ثورة صناعية رابعة.", e.title)
            if content:
                try:
                    res = self.x.create_tweet(text=f"📌 {content[:275]}")
                    if res:
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                            conn.commit()
                        logging.info("✅ تم النشر بنجاح.")
                        break
                except Exception as ex:
                    logging.error(f"❌ فشل النشر: {ex}")

    def run(self):
        self.process_smart_replies()
        self.execute_publishing()

if __name__ == "__main__":
    TechSupremeSystem().run()
