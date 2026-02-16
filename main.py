import os
import sqlite3
import logging
import time
import hashlib
import sys
import tweepy
from datetime import datetime
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
        self.db_path = "data/sovereign_v16.db"
        self._init_db()
        self.sys_instruction = (
            "Focus on Artificial Intelligence and its latest tools for individuals. Gulf dialect. "
            "NEVER mention 'Industrial Revolution', replace it with 'Artificial Intelligence and its latest tools'. "
            "Professional, no symbols, no Chinese characters."
        )
        self.competitor_accounts = ["competitor1", "competitor2"]  # استبدل بالحسابات الحقيقية

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

    # === نشر التغريدات أولًا ===
    def post_news_sequence(self, keyword):
        logging.info(f"🚀 معالجة الكلمة المفتاحية للنشر: {keyword}")

        main_prompt = f"اكتب خبر سكوب عن {keyword} بلهجة خليجية، ركز على فايدة الفرد."
        main_content = self._ask_ai(main_prompt)
        if not main_content:
            return None

        content_hash = hashlib.md5(main_content.encode()).hexdigest()
        if self._is_posted(content_hash):
            logging.info("⚠️ المحتوى مكرر، تم الإيقاف.")
            return None

        try:
            # نشر التغريدة الأساسية
            main_tweet = self.x_client.create_tweet(text=main_content)
            main_id = main_tweet.data["id"]
            self._mark_posted(content_hash, main_id, "main")
            logging.info("✅ تم نشر التغريدة الأساسية")

            # العقل الثاني (جوك)
            time.sleep(5)
            joke_prompt = f"بناءً على هذا الخبر: '{main_content}'، عطنا معلومة تقنية ممتعة وسريعة بلهجة خليجية."
            joke_content = self._ask_ai(joke_prompt)
            reply_1_id = None
            if joke_content:
                reply_1 = self.x_client.create_tweet(text=joke_content, in_reply_to_tweet_id=main_id)
                reply_1_id = reply_1.data["id"]
                logging.info("✅ تم نشر رد العقل الثاني (جوك)")

            # العقل الثالث (كوين)
            time.sleep(5)
            coin_prompt = f"اقترح أداة ذكاء اصطناعي مرتبطة بـ {keyword} تساعد الشخص في حياته اليومية، بلهجة خليجية."
            coin_content = self._ask_ai(coin_prompt)
            if coin_content and reply_1_id:
                self.x_client.create_tweet(text=f"💡 أداة ننصحك تجربها:\n{coin_content}", in_reply_to_tweet_id=reply_1_id)
                logging.info("✅ تم نشر رد العقل الثالث (كوين)")

            return main_id

        except Exception as e:
            if "429" in str(e):
                logging.error("🛑 خطأ 429: زحمة طلبات. خروج آمن.")
                sys.exit(0)
            logging.error(f"❌ فشل في تسلسل التغريدات: {e}")
            return None

    # === مراقبة المنافسين مع Retry ذكي ===
    def safe_get_tweets(self, account, retries=3):
        for i in range(retries):
            try:
                user_id = self.x_client.get_user(username=account).data.id
                return self.x_client.get_users_tweets(id=user_id, max_results=2)
            except Exception as e:
                if "429" in str(e):
                    wait_time = 60 * (i + 1)
                    logging.warning(f"Rate limit hit عند {account}. Waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Error fetching tweets for {account}: {e}")
                    return None

    def monitor_competitors(self):
        logging.info("🔍 مراقبة تغريدات المنافسين...")
        for account in self.competitor_accounts:
            tweets = self.safe_get_tweets(account)
            if tweets and tweets.data:
                for tweet in tweets.data:
                    logging.info(f"📌 {account}: {tweet.text[:50]}...")
            time.sleep(60)  # فاصل أمان بين الحسابات

if __name__ == "__main__":
    bot = SovereignBot()
    # نشر المحتوى أولًا
    targets = ["مساعدات الذكاء الاصطناعي الشخصية", "أدوات الفيديو بالذكاء الاصطناعي"]
    for target in targets:
        bot.post_news_sequence(target)
        logging.info("⏳ استراحة قصيرة قبل الكلمة التالية...")
        time.sleep(60)

    # بعد النشر، مراقبة المنافسين
    bot.monitor_competitors()
