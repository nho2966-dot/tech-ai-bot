import os
import sqlite3
import logging
import time
import hashlib
import sys
import feedparser
import tweepy
from datetime import datetime, timezone
from google import genai  # العقل الأساسي

# === إعداد تسجيل الأخطاء (Log) ===
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignBot:
    def __init__(self):
        # إعداد العقول والمنصات
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.db_path = "data/sovereign_v9.db"
        self._init_db()
        self.sys_instruction = (
            "Focus on Artificial Intelligence and its latest tools for individuals. Gulf dialect. "
            "NEVER mention 'Industrial Revolution', replace it with 'Artificial Intelligence and its latest tools'. "
            "Professional, no symbols, no Chinese characters."
        )

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS tweets (
                hash TEXT PRIMARY KEY, 
                tweet_id TEXT, 
                type TEXT, 
                ts DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

    def _is_posted(self, content_hash):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM tweets WHERE hash = ?", (content_hash,)).fetchone() is not None

    def _mark_posted(self, content_hash, tweet_id, t_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO tweets (hash, tweet_id, type) VALUES (?, ?, ?)", (content_hash, tweet_id, t_type))
            conn.commit()

    def _ask_ai(self, prompt):
        try:
            res = self.ai_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return res.text.strip()
        except Exception as e:
            logging.error(f"⚠️ خطأ في العقل: {e}")
            return None

    # === نظام العقول المتسلسلة المدمج ===
    def process_and_post(self, keyword):
        logging.info(f"🚀 معالجة الكلمة المفتاحية: {keyword}")

        # 1️⃣ العقل الأول (جمناي) - التغريدة الأساسية (الخبر)
        main_prompt = f"اكتب خبر سكوب عن {keyword} بلهجة خليجية، ركز على فايدة الفرد."
        main_content = self._ask_ai(main_prompt)
        if not main_content: return

        content_hash = hashlib.md5(main_content.encode()).hexdigest()
        if self._is_posted(content_hash):
            logging.info("⚠️ المحتوى مكرر، تم الإيقاف.")
            return

        try:
            # نشر التغريدة الأساسية
            main_tweet = self.x_client.create_tweet(text=main_content)
            main_id = main_tweet.data["id"]
            self._mark_posted(content_hash, main_id, "main")
            logging.info("✅ تم نشر التغريدة الأساسية")

            # 2️⃣ العقل الثاني (جوك) - الرد الأول (فائدة إضافية أو معلومة مرحة)
            time.sleep(5) # فاصل أمان
            joke_prompt = f"بناءً على هذا الخبر: '{main_content}'، عطنا معلومة تقنية 'جوك' ممتعة وسريعة للأفراد بلهجة خليجية."
            joke_content = self._ask_ai(joke_prompt)
            if joke_content:
                reply_1 = self.x_client.create_tweet(text=joke_content, in_reply_to_tweet_id=main_id)
                logging.info("✅ تم نشر رد العقل الثاني (جوك)")

            # 3️⃣ العقل الثالث (كوين) - الرد الثاني (أداة عملية للتحميل أو التجربة)
            time.sleep(5)
            coin_prompt = f"اقترح أداة ذكاء اصطناعي (AI Tool) مرتبطة بـ {keyword} تساعد الشخص في حياته اليومية، بلهجة خليجية."
            coin_content = self._ask_ai(coin_prompt)
            if coin_content:
                self.x_client.create_tweet(text=f"💡 أداة ننصحك تجربها:\n{coin_content}", in_reply_to_tweet_id=reply_1.data["id"])
                logging.info("✅ تم نشر رد العقل الثالث (كوين)")

        except Exception as e:
            if "429" in str(e):
                logging.error("🛑 خطأ 429: زحمة طلبات. خروج آمن.")
                sys.exit(0)
            logging.error(f"❌ فشل في تسلسل التغريدات: {e}")

if __name__ == "__main__":
    bot = SovereignBot()
    # كلمات استهدافية لعام 2026
    targets = ["مساعدات الذكاء الاصطناعي الشخصية", "أدوات الفيديو بالذكاء الاصطناعي"]
    for target in targets:
        bot.process_and_post(target)
        logging.info("⏳ استراحة محارب بين الكلمات...")
        time.sleep(60)
