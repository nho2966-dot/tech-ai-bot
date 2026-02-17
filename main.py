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
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignBot:
    def __init__(self):
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "x_api": os.getenv("X_API_KEY"),
            "x_secret": os.getenv("X_API_SECRET"),
            "x_token": os.getenv("X_ACCESS_TOKEN"),
            "x_token_secret": os.getenv("X_ACCESS_SECRET")
        }
        self._setup_brains()
        self._setup_x()
        self.db_path = "data/sovereign_v21.db"
        self._init_db()

    def _setup_brains(self):
        self.brain_primary = genai.Client(api_key=self.keys["gemini"]) if self.keys["gemini"] else None

    def _setup_x(self):
        try:
            # للنشر النصي v2
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=self.keys["x_api"],
                consumer_secret=self.keys["x_secret"],
                access_token=self.keys["x_token"],
                access_token_secret=self.keys["x_token_secret"]
            )
            # لرفع الصور v1.1
            auth = tweepy.OAuth1UserHandler(
                self.keys["x_api"], self.keys["x_secret"],
                self.keys["x_token"], self.keys["x_token_secret"]
            )
            self.api_v1 = tweepy.API(auth)
            logging.info("✅ X Media & Text Clients: Ready")
        except Exception as e:
            logging.error(f"❌ X Connection Failed: {e}")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, url TEXT, score REAL, ts DATETIME)")

    def _get_image_from_url(self, url):
        try:
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            img = soup.find("meta", property="og:image")
            return img["content"] if img else None
        except: return None

    def fetch_latest_ai_news(self):
        feeds = ["https://techcrunch.com/category/artificial-intelligence/feed/"]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                h = hashlib.md5(entry.link.encode()).hexdigest()
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): continue
                
                # تقييم سريع (بسيط لضمان الاستمرارية)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("INSERT OR REPLACE INTO waiting_room (hash, content, url, score, ts) VALUES (?, ?, ?, ?, ?)",
                                (h, entry.title, entry.link, 9.0, datetime.now(timezone.utc)))

    def run_cycle(self):
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            ready = conn.execute("SELECT hash, content, url FROM waiting_room WHERE ts < ?", (now - timedelta(minutes=5),)).fetchall()
            for h, content, url in ready:
                try:
                    # 1. صياغة النص بلهجة خليجية
                    prompt = f"صغ هذا الخبر بلهجة خليجية مهنية للأفراد: {content} - المصدر: {url}"
                    final_text = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
                    
                    # 2. جلب ورفع الصورة
                    media_ids = None
                    img_url = self._get_image_from_url(url)
                    if img_url:
                        img_data = requests.get(img_url).content
                        with BytesIO(img_data) as img_file:
                            media = self.api_v1.media_upload(filename="news.jpg", file=img_file)
                            media_ids = [media.media_id]

                    # 3. النشر النهائي
                    self.x_client.create_tweet(text=final_text[:275], media_ids=media_ids)
                    conn.execute("INSERT INTO history (hash, ts) VALUES (?, ?)", (h, now))
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info(f"🎯 Posted: {content}")
                except Exception as e: logging.error(f"❌ Cycle error: {e}")

if __name__ == "__main__":
    bot = SovereignBot()
    bot.fetch_latest_ai_news()
    bot.run_cycle()
