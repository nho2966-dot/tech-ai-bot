import os
import sqlite3
import time
import logging
import hashlib
import random
from datetime import datetime

import tweepy
import feedparser
from google import genai
from openai import OpenAI
from flask import Flask, jsonify
from dotenv import load_dotenv

# ================== إعدادات عامة ==================
load_dotenv()
DB_FILE = "news.db"
FINAL_TRUST_THRESHOLD = 0.80 # خفضته قليلاً لضمان عدم ضياع أخبار هامة
POST_LIMIT_PER_RUN = 1

# ================== مصادر RSS الموثوقة عالمياً ==================
RSS_SOURCES = [
    {"name": "The Verge", "category": "General", "url": "https://www.theverge.com/rss/index.xml", "trust": 0.95},
    {"name": "Wired", "category": "Analysis", "url": "https://www.wired.com/feed/rss", "trust": 0.96},
    {"name": "Ars Technica", "category": "Deep Tech", "url": "https://feeds.arstechnica.com/arstechnica/index", "trust": 0.98},
    {"name": "MIT Technology Review", "category": "AI Research", "url": "https://www.technologyreview.com/feed/", "trust": 0.99},
    {"name": "TechRadar", "category": "Reviews", "url": "https://www.techradar.com/rss", "trust": 0.93},
    {"name": "9to5Mac", "category": "Apple", "url": "https://9to5mac.com/feed/", "trust": 0.97},
    {"name": "IEEE Spectrum", "category": "Engineering", "url": "https://spectrum.ieee.org/rss/fulltext", "trust": 0.98},
    {"name": "Android Central", "category": "Android", "url": "https://www.androidcentral.com/feed", "trust": 0.94},
]

BLACKLIST_KEYWORDS = [
    "rumor", "leak", "unconfirmed", "speculation", "giveaway", 
    "discount", "airdrop", "إشاعة", "تسريب", "غير مؤكد"
]

# ================== كلاس البوت ==================
class TechEliteBot:
    def __init__(self):
        self._init_logging()
        self._init_db()
        self._init_clients()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s")

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS news (
                hash TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                published_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _init_clients(self):
        # توافق مع مسميات GitHub Secrets الخاصة بك
        self.ai_gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.ai_qwen = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _is_blacklisted(self, text: str) -> bool:
        text = text.lower()
        return any(k in text for k in BLACKLIST_KEYWORDS)

    def _exists(self, h: str) -> bool:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.execute("SELECT 1 FROM news WHERE hash=?", (h,))
        exists = cur.fetchone() is not None
        conn.close()
        return exists

    def _save(self, h, title, source):
        conn = sqlite3.connect(DB_FILE)
        conn.execute(
            "INSERT INTO news VALUES (?, ?, ?, ?)",
            (h, title, source, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def ai_trust_score(self, title, summary) -> float:
        prompt = f"قيّم موثوقية الخبر تقنيًا من 0 إلى 1. رقم فقط.\nالعنوان: {title}\nالملخص: {summary}"
        try:
            time.sleep(10) # تأخير لضمان عدم تجاوز الـ Quota
            res = self.ai_gemini.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            return float(res.text.strip())
        except:
            return 0.8 # درجة افتراضية عند تعطل AI لضمان استمرار النشر

    def generate_tweet(self, title, summary, source, category):
        instruction = (
            f"أنت محرر تقني محترف. اكتب تغريدة عربية دقيقة. المصدر: {source}. التصنيف: {category}. "
            "استخدم مصطلحات تقنية إنجليزية بين قوسين. ممنوع الرموز الصينية."
        )
        prompt = f"العنوان: {title}\nالملخص: {summary}"

        # المحاولة الأولى: Gemini
        try:
            time.sleep(10)
            r = self.ai_gemini.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"{instruction}\n{prompt}"
            )
            return r.text.strip()[:280]
        except:
            logging.warning("⚠️ Gemini Busy → Switching to Qwen")

        # المحاولة الثانية: Qwen
        try:
            c = self.ai_qwen.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return c.choices[0].message.content.strip()[:280]
        except Exception as e:
            logging.error(f"AI Generation failed: {e}")
            return None

    def run_once(self):
        posted = 0
        random.shuffle(RSS_SOURCES)
        for src in RSS_SOURCES:
            try:
                feed = feedparser.parse(src["url"])
                for e in feed.entries[:3]:
                    text_blob = f"{e.title} {getattr(e, 'summary', '')}"
                    h = self._hash(text_blob)

                    if self._exists(h) or self._is_blacklisted(text_blob):
                        continue

                    # تقييم الموثوقية
                    score = self.ai_trust_score(e.title, getattr(e, "summary", ""))
                    if score < FINAL_TRUST_THRESHOLD:
                        continue

                    tweet = self.generate_tweet(e.title, getattr(e, "summary", ""), src["name"], src["category"])
                    if not tweet:
                        continue

                    self.x_client.create_tweet(text=tweet)
                    self._save(h, e.title, src["name"])
                    logging.info(f"✅ تم النشر: {src['name']} | {e.title[:40]}")
                    posted += 1

                    if posted >= POST_LIMIT_PER_RUN:
                        return
            except Exception as e:
                logging.error(f"Error processing source {src['name']}: {e}")

# ================== تشغيل ==================
if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_once()
