import os
import sqlite3
import hashlib
import tweepy
import feedparser
import logging
import random
import time
from datetime import datetime, date, timedelta
from openai import OpenAI
from google import genai

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignBotV6:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS queue (hash TEXT PRIMARY KEY, data TEXT, added_at DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (id TEXT PRIMARY KEY)")

    def _setup_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    # --- إدارة سقف النشر ---
    def can_post_original(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            return (res[0] if res else 0) < 3

    def increment_post_count(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
            conn.commit()

    # --- عقل الردود الاستهدافية مع فاصل زمني ---
    def handle_smart_replies(self):
        try:
            logging.info("🔎 جاري فحص المنشنات...")
            mentions = self.x_client.get_users_mentions(id=self.x_client.get_me().data.id, max_results=5)
            if not mentions.data: return

            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if not conn.execute("SELECT 1 FROM replies WHERE id=?", (tweet.id,)).fetchone():
                        # توليد رد خليجي ذكي
                        prompt = f"رد بأسلوب تقني خليجي ذكي ومختصر جداً على: {tweet.text}"
                        res = self.openai.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                        reply_txt = res.choices[0].message.content.strip()
                        
                        # فاصل زمني عشوائي قبل الرد (بين 10 إلى 30 ثانية)
                        wait = random.randint(10, 30)
                        logging.info(f"⏳ انتظار {wait} ثانية قبل الرد على {tweet.id}")
                        time.sleep(wait)
                        
                        self.x_client.create_tweet(text=reply_txt, in_reply_to_tweet_id=tweet.id)
                        conn.execute("INSERT INTO replies VALUES (?)", (tweet.id,))
                        conn.commit()
                        logging.info(f"✅ تم الرد على {tweet.id}")
        except Exception as e:
            logging.warning(f"⚠️ تنبيه الردود: {e}")

    # --- دورة النشر الإستراتيجي مع فاصل زمني ---
    def run_publishing_cycle(self):
        if not self.can_post_original():
            logging.info("🛡️ تم بلوغ الحد اليومي (3 تغريدات).")
            return

        with sqlite3.connect(self.db_path) as conn:
            threshold = datetime.now() - timedelta(minutes=20)
            queued = conn.execute("SELECT hash, data FROM queue WHERE added_at <= ?", (threshold,)).fetchall()
            
            for h, data in queued:
                # العقول الأربعة (تبسيط للمثال)
                impact_score = 9.0 # افتراضياً للتجربة
                if impact_score >= 8.5:
                    # صياغة نهائية
                    instr = "أنت محرر تقني خليجي. صغ هذا الخبر للأفراد بأسلوب احترافي مدفوع."
                    res = self.openai.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": instr}, {"role": "user", "content": data}])
                    final_txt = res.choices[0].message.content.strip()

                    # فاصل زمني قبل النشر (بين دقيقة ودقيقتين لضمان الهدوء)
                    wait_publish = random.randint(60, 120)
                    logging.info(f"⏳ انتظار {wait_publish} ثانية قبل النشر لكسر النمط الآلي.")
                    time.sleep(wait_publish)

                    self.x_client.create_tweet(text=final_txt)
                    self.increment_post_count()
                    conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                    logging.info("🚀 تم نشر التغريدة الإستراتيجية.")
                
                conn.execute("DELETE FROM queue WHERE hash=?", (h,))
                conn.commit()
                break # نشر واحد فقط في الدورة

    def run(self):
        # 1. الردود أولاً
        self.handle_smart_replies()
        
        # 2. فاصل بين الردود والنشر (30 ثانية) لعدم إرباك الـ API
        time.sleep(30)
        
        # 3. النشر الإستراتيجي
        self.run_publishing_cycle()

        # 4. جلب أخبار جديدة للطابور
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        for entry in feed.entries[:3]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR IGNORE INTO queue VALUES (?, ?, ?)", (h, entry.title, datetime.now()))
                    conn.commit()

if __name__ == "__main__":
    SovereignBotV6().run()
