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

# إعداد السجلات بهيبة تقنية
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignSequentialSystem:
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
        """نظام العقول المتتابعة: OpenAI أولاً، ثم Gemini كبديل فوري"""
        # العقل الأول: OpenAI
        try:
            res = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
            )
            logging.info("🧠 تم التنفيذ بواسطة العقل الأول (OpenAI)")
            return res.choices[0].message.content.strip()
        except Exception as e:
            logging.warning(f"⚠️ العقل الأول متعثر (429/Limit).. تفعيل العقل الثاني فوراً.")
            
        # العقل الثاني: Gemini (نظام الفشل التلقائي)
        try:
            res = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_prompt}\n\nالمحتوى المطلوب معالجته: {user_content}"
            )
            logging.info("🧠 تم التنفيذ بواسطة العقل الثاني (Gemini)")
            return res.text.strip()
        except Exception as e:
            logging.error(f"❌ تعطلت العقول المتتابعة: {e}")
            return None

    def handle_smart_replies(self):
        """الردود الاستهدافية: فاصل زمني (20-40 ثانية) وبدون ليميت يومي"""
        try:
            me = self.x_client.get_me()
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions or not mentions.data: return

            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if not conn.execute("SELECT 1 FROM replies WHERE id=?", (tweet.id,)).fetchone():
                        # استدعاء العقول المتتابعة للرد
                        reply_txt = self.execute_sequential_brain(
                            "أنت خبير تقني خليجي متمكن. رد بذكاء واختصار شديد بلهجة بيضاء.",
                            tweet.text
                        )
                        if reply_txt:
                            time.sleep(random.randint(20, 40)) # فاصل زمني بشري
                            self.x_client.create_tweet(text=reply_txt, in_reply_to_tweet_id=tweet.id)
                            conn.execute("INSERT INTO replies VALUES (?)", (tweet.id,))
                            conn.commit()
                            logging.info(f"✅ تم الرد المتتابع على: {tweet.id}")
        except Exception as e:
            logging.warning(f"⚠️ تنبيه X API في الردود: {e}")

    def run_publishing_cycle(self):
        """النشر الإستراتيجي: فاصل زمني (60-120 ثانية) وسقف 3 تغريدات"""
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            if res and res[0] >= 3:
                logging.info(f"🛡️ سقف النشر مكتمل اليوم ({res[0]}/3).")
                return

            threshold = datetime.now() - timedelta(minutes=20)
            queued = conn.execute("SELECT hash, data FROM queue WHERE added_at <= ?", (threshold,)).fetchall()
            
            for h, data in queued:
                # استدعاء العقول المتتابعة للصياغة
                final_txt = self.execute_sequential_brain(
                    "أنت محرر تقني خليجي. صغ الخبر بأسلوب 'الزبدة' للأفراد، ركز على التقنيات الحديثة.",
                    data
                )
                if final_txt:
                    time.sleep(random.randint(60, 120)) # فاصل أمان ثقيل
                    try:
                        self.x_client.create_tweet(text=final_txt)
                        conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
                        conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                        conn.commit()
                        logging.info("🚀 تم النشر بنجاح عبر العقول المتتابعة.")
                        break 
                    except Exception as e:
                        logging.error(f"❌ فشل النشر في X: {e}")

    def run(self):
        # تنفيذ المهام بتتابع ذكي
        self.run_publishing_cycle() # النشر أولاً
        time.sleep(30) # فاصل بين النشر والرد
        self.handle_smart_replies() # الردود الاستهدافية
        
        # تغذية الطابور
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        for entry in feed.entries[:5]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR IGNORE INTO queue VALUES (?, ?, ?)", (h, entry.title, datetime.now()))
                    conn.commit()

if __name__ == "__main__":
    SovereignSequentialSystem().run()
