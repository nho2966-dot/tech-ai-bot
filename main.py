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
from dotenv import load_dotenv

load_dotenv()
DB_FILE = "news.db"
POST_LIMIT_PER_RUN = 1

RSS_SOURCES = [
    {"name": "The Verge", "category": "General", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "category": "Analysis", "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "category": "Deep Tech", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "9to5Mac", "category": "Apple", "url": "https://9to5mac.com/feed/"},
    {"name": "Android Central", "category": "Android", "url": "https://www.androidcentral.com/feed"}
]

class TechEliteBot:
    def __init__(self):
        self._init_logging()
        self._setup_db() # إصلاح وتجهيز القاعدة
        self._init_clients()
        self._get_my_id()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s")

    def _setup_db(self):
        """دالة ذكية لإنشاء أو تحديث الجداول لتجنب خطأ no such column"""
        conn = sqlite3.connect(DB_FILE)
        # حذف الجداول القديمة لضمان هيكلة نظيفة (Reset لمرة واحدة)
        try:
            conn.execute("DROP TABLE IF EXISTS news")
            conn.execute("DROP TABLE IF EXISTS replies")
            conn.execute("""CREATE TABLE news 
                         (hash TEXT PRIMARY KEY, title TEXT, source TEXT, published_at TEXT)""")
            conn.execute("CREATE TABLE replies (tweet_id TEXT PRIMARY KEY)")
            conn.commit()
            logging.info("✅ Database reconstructed successfully.")
        except Exception as e:
            logging.error(f"DB Setup Error: {e}")
        finally:
            conn.close()

    def _init_clients(self):
        self.ai_gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )

    def _get_my_id(self):
        try:
            res = self.x_client.get_me()
            self.my_id = res.data.id
        except:
            self.my_id = None

    def ai_ask(self, instruction, prompt):
        try:
            time.sleep(10)
            res = self.ai_gemini.models.generate_content(model="gemini-1.5-flash", contents=f"{instruction}\n{prompt}")
            return res.text.strip()
        except:
            try:
                c = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": instruction}, {"role": "user", "content": prompt}]
                )
                return c.choices[0].message.content.strip()
            except: return None

    def handle_mentions(self):
        if not self.my_id: return
        try:
            mentions = self.x_client.get_users_mentions(id=self.my_id, max_results=5)
            if not mentions or not mentions.data: return
            
            conn = sqlite3.connect(DB_FILE)
            for tweet in mentions.data:
                if conn.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone():
                    continue
                
                reply = self.ai_ask("خبير تقني. رد بذكاء واختصار بالعربية.", tweet.text)
                if reply:
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO replies VALUES (?)", (str(tweet.id),))
                    conn.commit()
            conn.close()
        except Exception as e: logging.error(f"Mentions Error: {e}")

    def run_news_cycle(self):
        posted = 0
        random.shuffle(RSS_SOURCES)
        for src in RSS_SOURCES:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:3]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone()
                conn.close()

                if exists: continue
                
                tweet_text = self.ai_ask(f"اكتب تغريدة تقنية (المصدر: {src['name']}). مصطلحات إنجليزية بين قوسين.", e.title)
                if tweet_text:
                    try:
                        self.x_client.create_tweet(text=tweet_text[:280])
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("INSERT INTO news VALUES (?, ?, ?, ?)", (h, e.title, src["name"], datetime.utcnow().isoformat()))
                        conn.commit()
                        conn.close()
                        logging.info(f"✅ Posted: {e.title[:30]}")
                        posted += 1
                        if posted >= POST_LIMIT_PER_RUN: return
                    except Exception as e: logging.error(f"Post Error: {e}")

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.handle_mentions()
    bot.run_news_cycle()
