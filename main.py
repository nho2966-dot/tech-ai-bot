import os
import sqlite3
import time
import logging
import hashlib
import random
from datetime import datetime

import tweepy
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

# ================== إعدادات عامة ==================
load_dotenv()
DB_FILE = "news.db"

# مصادر التسريبات والأخبار الاستراتيجية
RSS_SOURCES = [
    {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"},
    {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"}
]

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, summary TEXT, published_at TEXT)")
        conn.close()

    def _init_clients(self):
        # 1. إعداد Gemini (مطابق لاسم GEMINI_KEY في الصورة)
        try:
            self.gemini_client = genai.Client(
                api_key=os.getenv("GEMINI_KEY"),
                http_options={'api_version': 'v1'}
            )
        except Exception as e:
            logging.error(f"Gemini Init Error: {e}")

        # 2. إعداد OpenRouter كبديل (OPENROUTER_API_KEY)
        self.ai_qwen = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"), 
            base_url="https://openrouter.ai/api/v1"
        )
        
        # 3. إعداد عميل X (Twitter) - مطابقة تامة لمسمياتك في الصورة
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def ai_ask(self, system_prompt, user_content):
        """محاولة Gemini ثم التبديل لـ Qwen في حال الفشل"""
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_prompt}\n\n{user_content}"
            )
            return response.text.strip()
        except Exception as e:
            logging.warning(f"⚠️ Gemini Error, using Qwen: {e}")
            try:
                c = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                )
                return c.choices[0].message.content.strip()
            except:
                return None

    def post_backup_content(self):
        """خطة الطوارئ عند عدم وجود أخبار"""
        logging.info("🔄 جاري نشر محتوى تفاعلي احتياطي...")
        prompt = "اكتب تغريدة تفاعلية (نصيحة أو سؤال) عن مستقبل Nvidia و Apple في 2026. اجعلها بأسلوب Elite."
        content = self.ai_ask("خبير تقني سعودي محترف.", prompt)
        if content:
            try:
                self.x_client.create_tweet(text=content[:280])
                logging.info("✅ تم النشر الاحتياطي.")
            except Exception as e:
                logging.error(f"X Backup Error: {e}")

    def run_news_cycle(self):
        random.shuffle(RSS_SOURCES)
        news_posted = False

        for src in RSS_SOURCES:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone()
                conn.close()
                if exists: continue

                # فلاتر التسريبات والعمالقة
                is_leak = any(w in e.title.lower() for w in ["leak", "rumor", "تسريب", "internal"])
                is_major = any(w in e.title.lower() for w in ["apple", "nvidia", "google", "openai", "ai"])

                if is_leak or is_major:
                    prompt = "صغ الخبر بأسلوب (Elite) مع إيموجي ومصطلحات تقنية إنجليزية. إذا كان تسريباً ابدأ بـ 🚨."
                    tweet_text = self.ai_ask(prompt, e.title)
                    
                    if tweet_text:
                        try:
                            self.x_client.create_tweet(text=tweet_text[:280])
                            conn = sqlite3.connect(DB_FILE)
                            conn.execute("INSERT INTO news VALUES (?, ?, ?, ?)", (h, e.title, "", datetime.utcnow().isoformat()))
                            conn.commit()
                            conn.close()
                            logging.info(f"🚀 تم نشر الخبر: {e.title[:30]}")
                            news_posted = True
                            return
                        except Exception as ex:
                            logging.error(f"X Post Error: {ex}")

        if not news_posted:
            self.post_backup_content()

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_news_cycle()
