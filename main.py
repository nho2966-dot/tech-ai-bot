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
import google.generativeai as genai

load_dotenv()
DB_FILE = "news.db"
POST_LIMIT_PER_RUN = 1
MIN_CREDIBILITY_SCORE = 50 # خفضناه قليلاً لضمان مرونة أكبر في البداية

# ================== المصادر والكلمات المفتاحية ==================
RSS_SOURCES = [
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"}, # ملك التسريبات لآبل
    {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"}, # تسريبات حصرية
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"}, # تسريبات جوجل وسامسونج
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"}
]

# إضافة "Leak" و "Rumor" للكلمات المفتاحية
TECH_KEYWORDS = ["AI", "GPT", "Apple", "Nvidia", "Leak", "Rumor", "تسريب", "Preview", "Internal"]

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
        genai.configure(api_key=os.getenv("GEMINI_KEY"))
        self.gemini = genai.GenerativeModel('gemini-1.5-flash')
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )
        try: self.my_id = self.x_client.get_me().data.id
        except: self.my_id = None

    def ai_ask(self, system_prompt, user_content):
        try:
            res = self.gemini.generate_content(f"{system_prompt}\n\n{user_content}")
            return res.text.strip()
        except:
            try:
                c = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                )
                return c.choices[0].message.content.strip()
            except: return None

    def post_backup_content(self):
        """نشر محتوى بديل: استطلاع رأي أو نصيحة توظيف AI"""
        logging.info("🔄 محرك الاحتياط: جاري إنشاء محتوى تفاعلي...")
        prompts = [
            "صغ استطلاع رأي تقني (Poll) حول صراع عمالقة التقنية أو مستقبل الـ AI. اكتب نص التغريدة فقط.",
            "قدم نصيحة ذهبية لكيفية توظيف الذكاء الاصطناعي في اختصار ٤ ساعات من العمل اليومي.",
            "اكتب تغريدة عن 'تسريب متوقع' بخصوص آيفون القادم أو معالجات Nvidia بناءً على الاتجاهات الحالية."
        ]
        content = self.ai_ask("خبير تقني سعودي ذكي. صغ المحتوى بأسلوب فخم وجذاب.", random.choice(prompts))
        if content:
            try:
                self.x_client.create_tweet(text=content[:280])
                logging.info("✅ تم نشر محتوى بديل/تفاعلي.")
            except Exception as e: logging.error(f"Backup Post Error: {e}")

    def run_news_cycle(self):
        random.shuffle(RSS_SOURCES)
        news_posted = False

        for src in RSS_SOURCES:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    conn.close()
                    continue
                conn.close()

                # التحقق من الأهمية (تسريبات أو أخبار عمالقة)
                is_leak = any(w in e.title.lower() for w in ["leak", "rumor", "internal", "تسريب"])
                is_major = any(w in e.title.lower() for w in ["apple", "nvidia", "google", "openai"])

                if not (is_leak or is_major): continue

                prompt = "صغ هذا الخبر/التسريب في تغريدة 'نخبة'. إذا كان تسريباً، ابدأ بعبارة مثيرة (مثلاً: تسريبات حصرية 🚨). استخدم مصطلحات إنجليزية."
                tweet_text = self.ai_ask(prompt, e.title)

                if tweet_text:
                    try:
                        self.x_client.create_tweet(text=tweet_text[:280])
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("INSERT INTO news VALUES (?, ?, ?, ?)", (h, e.title, "", datetime.utcnow().isoformat()))
                        conn.commit()
                        conn.close()
                        logging.info(f"🚀 تم النشر: {e.title[:30]}")
                        news_posted = True
                        return # نكتفي بخبر واحد ثم نخرج
                    except Exception as ex: logging.error(f"X Post Error: {ex}")

        if not news_posted:
            self.post_backup_content()

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_news_cycle()
