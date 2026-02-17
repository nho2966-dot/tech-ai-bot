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

logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignSequentialSystemV10:
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
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    def execute_sequential_brain(self, system_prompt, user_content):
        """نظام العقول المتتابعة كما تم الاتفاق عليه"""
        try:
            res = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
            )
            return res.choices[0].message.content.strip()
        except:
            logging.warning("⚠️ العقل الأول تعثر.. الانتقال للعقل الثاني.")
            try:
                res = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{system_prompt}\n\n{user_content}"
                )
                return res.text.strip()
            except: return None

    def handle_smart_replies(self):
        """الردود مع 'تكتيك الهدوء' لتجنب 429"""
        try:
            # تقليل النتائج لـ 2 فقط لتقليل ضغط الـ API في البداية
            mentions = self.x_client.get_users_mentions(id=self.x_client.get_me().data.id, max_results=2)
            if not mentions or not mentions.data: return

            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if not conn.execute("SELECT 1 FROM replies WHERE id=?", (tweet.id,)).fetchone():
                        reply_txt = self.execute_sequential_brain(
                            "أنت تقني خليجي. رد بذكاء واختصار.", tweet.text
                        )
                        if reply_txt:
                            time.sleep(random.randint(40, 60)) # زيادة الفاصل ليكون بشرياً
                            self.x_client.create_tweet(text=reply_txt, in_reply_to_tweet_id=tweet.id)
                            conn.execute("INSERT INTO replies VALUES (?)", (tweet.id,))
                            conn.commit()
                            logging.info(f"✅ تم الرد.")
        except Exception as e:
            logging.warning(f"🛡️ X API مزدحم حالياً، سيتم المحاولة لاحقاً.")

    def run_publishing_cycle(self):
        """النشر بحد أقصى 3 يومياً وفواصل طويلة"""
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            if res and res[0] >= 3: return

            threshold = datetime.now() - timedelta(minutes=20)
            queued = conn.execute("SELECT hash, data FROM queue WHERE added_at <= ?", (threshold,)).fetchall()
            
            for h, data in queued:
                final_txt = self.execute_sequential_brain(
                    "صغ هذا الخبر التقني بأسلوب خليجي راقٍ ومختصر للأفراد.", data
                )
                if final_txt:
                    time.sleep(random.randint(90, 180)) # فاصل زمني طويل جداً للنشر
                    try:
                        self.x_client.create_tweet(text=final_txt)
                        conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
                        conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                        conn.commit()
                        logging.info("🚀 تم النشر.")
                        break 
                    except: pass

    def run(self):
        # تنفيذ دورة العمل
        self.run_publishing_cycle()
        time.sleep(60) # راحة دقيقة بين النشر وفحص المنشن
        self.handle_smart_replies()
        
        # تحديث الطابور
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        for entry in feed.entries[:5]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR IGNORE INTO queue VALUES (?, ?, ?)", (h, entry.title, datetime.now()))
                    conn.commit()

if __name__ == "__main__":
    SovereignSequentialSystemV10().run()
