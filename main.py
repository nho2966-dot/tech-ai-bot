import os
import sys
import time
import yaml
import random
import sqlite3
import pathlib
import requests
import feedparser
import tweepy
import logging
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# إعدادات التسجيل - إمبراطورية ناصر التقنية
logging.basicConfig(level=logging.INFO, format="🛡️ [أيبكس]: %(message)s")

class NasserApexBot:
    def __init__(self):
        self.config = self._load_config()
        self._init_db()
        self._init_clients()
        logging.info(f"🚀 أيبكس جاهز للعمل. التوثيق: {'نشط' if self.config['bot'].get('is_premium') else 'غير نشط'}")

    def _load_config(self):
        # بحث ذكي عن ملف الإعدادات لتجنب خطأ FileNotFoundError
        possible_paths = [
            pathlib.Path("config.yaml"),
            pathlib.Path(__file__).parent / "config.yaml",
            pathlib.Path("data/config.yaml")
        ]
        for path in possible_paths:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
        raise FileNotFoundError("❌ ملف config.yaml مفقود! تأكد من رفعه للمستودع.")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.config['bot']['database_path']) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied (id TEXT PRIMARY KEY)")

    def _init_clients(self):
        # إعداد عميل X
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        # تم تعطيل الواتساب بناءً على طلبك يا ناصر
        self.has_wa = False 

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, mode, inp=""):
        sys_p = self.config['prompts']['system_core']
        task_p = self.config['prompts']['modes'][mode].format(content=inp)
        
        for m_cfg in self.config['models']['priority']:
            try:
                key = os.getenv(m_cfg['env_key'])
                if not key: continue
                if m_cfg['type'] == "google":
                    res = genai.Client(api_key=key).models.generate_content(model=m_cfg['model'], contents=f"{sys_p}\n{task_p}")
                    return res.text.strip()
                else:
                    base = "https://api.x.ai/v1" if m_cfg['type']=="xai" else None
                    client = OpenAI(api_key=key, base_url=base)
                    res = client.chat.completions.create(model=m_cfg['model'], messages=[{"role":"user","content":f"{sys_p}\n{task_p}"}])
                    return res.choices[0].message.content.strip()
            except: continue
        return None

    def handle_mentions(self):
        try:
            me = self.x_client.get_me()
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions or not mentions.data: return
            for tweet in mentions.data:
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM replied WHERE id=?", (str(tweet.id),)).fetchone(): continue
                reply = self.generate("REPLY", tweet.text)
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO replied VALUES (?)", (str(tweet.id),))
                    time.sleep(random.randint(30, 60))
        except: pass

    def run_mission(self):
        m_type = random.choices(["SCOOP", "INFO", "CONTEST"], weights=[50, 25, 25])[0]
        logging.info(f"🎯 المهمة المجدولة: {m_type}")

        if m_type == "SCOOP":
            for feed_cfg in self.config['sources']['rss_feeds']:
                feed = feedparser.parse(feed_cfg['url'])
                if not feed.entries: continue
                entry = feed.entries[0]
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM processed WHERE id=?", (entry.link,)).fetchone(): continue
                
                source_tag = "@verge" if "theverge" in entry.link else "@TechCrunch"
                tweet = self.generate("POST_DEEP", f"المصدر: {source_tag} | المحتوى: {entry.title} {entry.description}")
                if tweet:
                    self.publish(tweet)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO processed VALUES (?)", (entry.link,))
                    break
        else:
            topic = "أدوات الذكاء الاصطناعي في عُمان" if m_type == "CONTEST" else "مقارنة تقنية مفيدة"
            tweet = self.generate(f"POST_{m_type}", topic)
            if tweet: self.publish(tweet)

    def publish(self, text):
        try:
            h = hashlib.sha256(text.encode()).hexdigest()
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): return
            
            self.x_client.create_tweet(text=text)
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
            logging.info("🚀 تم النشر على X بنجاح!")
            # تخطي إشعار الواتساب بصمت
        except Exception as e: logging.error(f"❌ خطأ في النشر: {e}")

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.handle_mentions()
    bot.run_mission()
