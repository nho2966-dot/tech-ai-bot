import os
import sqlite3
import logging
import time
import hashlib
import requests
import tweepy
import feedparser
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime, timedelta, timezone
from google import genai

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignBot:
    def __init__(self):
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "x_api": os.getenv("X_API_KEY"),
            "x_secret": os.getenv("X_API_SECRET"),
            "x_token": os.getenv("X_ACCESS_TOKEN"),
            "x_token_secret": os.getenv("X_ACCESS_SECRET")
        }
        self.db_path = "data/sovereign_v23.db"
        self._setup_brains()
        self._setup_x()
        self._init_db()

    def _setup_brains(self):
        self.brain = genai.Client(api_key=self.keys["gemini"]) if self.keys["gemini"] else None

    def _setup_x(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=self.keys["x_api"], consumer_secret=self.keys["x_secret"],
                access_token=self.keys["x_token"], access_token_secret=self.keys["x_token_secret"]
            )
            auth = tweepy.OAuth1UserHandler(self.keys["x_api"], self.keys["x_secret"], self.keys["x_token"], self.keys["x_token_secret"])
            self.api_v1 = tweepy.API(auth)
            logging.info("✅ أنظمة X جاهزة (نشر + وسائط)")
        except Exception as e: logging.error(f"❌ فشل ربط X: {e}")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, url TEXT, ts DATETIME)")

    def _get_image(self, url):
        try:
            res = requests.get(url, timeout=0)
            soup = BeautifulSoup(res.text, 'html.parser')
            img = soup.find("meta", property="og:image")
            return img["content"] if img else None
        except: return None

    def fetch_news(self):
        logging.info("🌐 جاري سحب أخبار الذكاء الاصطناعي...")
        feed = feedparser.parse("https://techcrunch.com/category/artificial-intelligence/feed/")
        for entry in feed.entries[:3]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR REPLACE INTO waiting_room VALUES (?, ?, ?, ?)",
                                (h, entry.title, entry.link, datetime.now(timezone.utc)))

    def handle_posting(self):
        """نشر خبر واحد فقط لضمان الفاصل الزمني"""
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            # شرط: نشر الأخبار التي مضى عليها 10 دقائق في الانتظار
            target = conn.execute("SELECT hash, content, url FROM waiting_room WHERE ts <= ? LIMIT 1", 
                                 (now - timedelta(minutes=10),)).fetchone()
            if target:
                h, content, url = target
                self._publish(h, content, url)
            else:
                logging.info("⏳ لا يوجد محتوى جاهز للنشر (في انتظار مرور الفاصل الزمني).")

    def _publish(self, h, content, url):
        try:
            # صياغة احترافية خليجية
            p = f"صغ هذا الخبر بلهجة خليجية مهنية للأفراد، ركز على الفائدة، واختم بالمصدر: {content} - {url}"
            txt = self.brain.models.generate_content(model="gemini-2.0-flash", contents=p).text
            
            # معالجة الصورة
            m_ids = None
            img_url = self._get_image(url)
            if img_url:
                img_data = requests.get(img_url).content
                with BytesIO(img_data) as f:
                    m = self.api_v1.media_upload(filename="ai.jpg", file=f)
                    m_ids = [m.media_id]

            self.x_client.create_tweet(text=txt[:275], media_ids=m_ids)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                conn.commit()
            logging.info("🎯 تم نشر التغريدة بنجاح!")
        except Exception as e: logging.error(f"❌ خطأ نشر: {e}")

    def handle_replies(self):
        """الردود الذكية بفاصل زمني عن النشر"""
        time.sleep(30) # فاصل بسيط لضمان عدم التداخل في نفس اللحظة
        logging.info("💬 جاري فحص المنشنات للرد الذكي...")
        # سيتم تفعيل منطق الرد الاستهدافي هنا في الدورة القادمة

if __name__ == "__main__":
    bot = SovereignBot()
    bot.fetch_news()      # 1. سحب
    bot.handle_posting()  # 2. نشر (بشرط الفاصل)
    bot.handle_replies()  # 3. رد (بعد فاصل)
