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
from google import genai  # المكتبة الجديدة المستقرة

# ================== إعدادات عامة ==================
load_dotenv()
DB_FILE = "news.db"
POST_LIMIT_PER_RUN = 1
MIN_CREDIBILITY_SCORE = 50

# ================== المصادر الموثوقة ==================
RSS_SOURCES = [
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"},
    {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"}
]

TECH_KEYWORDS = ["AI", "GPT", "Apple", "Nvidia", "Leak", "Rumor", "تسريب", "Preview", "Internal", "Google", "OpenAI"]

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, summary TEXT, published_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY)")
        conn.close()

    def _init_clients(self):
        # تهيئة مكتبة Google GenAI الجديدة
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        
        # تهيئة OpenRouter كبديل
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        
        # تهيئة X (Twitter)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )
        try:
            self.my_id = self.x_client.get_me().data.id
        except:
            self.my_id = None

    def ai_ask(self, system_prompt, user_content):
        """طلب الذكاء الاصطناعي مع معالجة المكتبة الجديدة والتبديل للبديل"""
        try:
            # طريقة استدعاء Gemini 1.5 Flash بالمكتبة الجديدة
            response = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_prompt}\n\n{user_content}"
            )
            return response.text.strip()
        except Exception as e:
            logging.warning(f"⚠️ Gemini Error, trying Qwen: {e}")
            try:
                c = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                )
                return c.choices[0].message.content.strip()
            except:
                return None

    def post_backup_content(self):
        """خطة الطوارئ: نصيحة تقنية أو استطلاع رأي"""
        logging.info("🔄 جاري إنشاء محتوى تفاعلي احتياطي...")
        prompts = [
            "صغ استطلاع رأي تقني (Poll) حول مستقبل الـ AI في ٢٠٢٦. اكتب نص التغريدة فقط.",
            "قدم نصيحة احترافية لكيفية استخدام AI في تحسين الإنتاجية.",
            "اكتب توقعاً تقنياً مبنياً على تسريبات عمالقة التكنولوجيا لهذا العام."
        ]
        content = self.ai_ask("أنت خبير تقني سعودي ذكي.", random.choice(prompts))
        if content:
            try:
                self.x_client.create_tweet(text=content[:280])
                logging.info("✅ تم نشر المحتوى الاحتياطي.")
            except Exception as e:
                logging.error(f"Backup Error: {e}")

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

                # فلترة ذكية (تسريبات أو عمالقة)
                is_leak = any(w in e.title.lower() for w in ["leak", "rumor", "تسريب", "internal"])
                is_major = any(w in e.title.lower() for w in ["apple", "nvidia", "google", "openai"])

                if is_leak or is_major:
                    prompt = "صغ الخبر كخبير تقني. إذا كان تسريباً ابدأ بـ (تسريب 🚨). استخدم مصطلحات إنجليزية تقنية."
                    tweet_text = self.ai_ask(prompt, e.title)
                    
                    if tweet_text:
                        try:
                            self.x_client.create_tweet(text=tweet_text[:280])
                            conn = sqlite3.connect(DB_FILE)
                            conn.execute("INSERT INTO news VALUES (?, ?, ?, ?)", (h, e.title, "", datetime.utcnow().isoformat()))
                            conn.commit()
                            conn.close()
                            logging.info(f"🚀 تم النشر بنجاح: {e.title[:30]}")
                            news_posted = True
                            return
                        except Exception as ex:
                            logging.error(f"X Post Error: {ex}")

        if not news_posted:
            self.post_backup_content()

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_news_cycle()
