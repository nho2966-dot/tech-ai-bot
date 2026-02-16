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

class SovereignBotV16:
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
            "Professional, no symbols, no Chinese characters. Avoid repetition."
        )

        # قائمة المنافسين المستهدفين لمراقبة المحتوى
        self.competitor_accounts = ["TechCrunch", "verge", "AI_Tools_News"]

    # === قاعدة البيانات ===
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
            conn.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                account TEXT, 
                tweet_id TEXT PRIMARY KEY,
                content TEXT,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

    def _is_posted(self, content_hash):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM tweets WHERE hash = ?", (content_hash,)).fetchone() is not None

    def _mark_posted(self, content_hash, tweet_id, t_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO tweets (hash, tweet_id, type) VALUES (?, ?, ?)", (content_hash, tweet_id, t_type))
            conn.commit()

    # === استدعاء العقل ===
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

    # === مراقبة المنافسين ===
    def monitor_competitors(self):
        logging.info("🔍 مراقبة تغريدات المنافسين...")
        for account in self.competitor_accounts:
            try:
                tweets = self.x_client.get_users_tweets(id=self._get_user_id(account), max_results=5)
                if tweets.data:
                    with sqlite3.connect(self.db_path) as conn:
                        for t in tweets.data:
                            conn.execute(
                                "INSERT OR IGNORE INTO competitors (account, tweet_id, content) VALUES (?, ?, ?)",
                                (account, t.id, t.text)
                            )
                        conn.commit()
            except Exception as e:
                logging.warning(f"⚠️ فشل مراقبة {account}: {e}")
        logging.info("✅ انتهاء مراقبة المنافسين.")

    def _get_user_id(self, username):
        user = self.x_client.get_user(username=username)
        return user.data.id

    # === تقييم الهيمنة المحتوى ===
    def dominance_score(self, keyword):
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM competitors").fetchone()[0] or 1
            keyword_count = conn.execute("SELECT COUNT(*) FROM competitors WHERE content LIKE ?", (f"%{keyword}%",)).fetchone()[0]
            score = round((keyword_count / total) * 100, 2)
            logging.info(f"📊 هيمنة كلمة '{keyword}': {score}%")
            return score

    # === عملية نشر متسلسلة ===
    def process_and_post(self, keyword):
        logging.info(f"🚀 معالجة الكلمة المفتاحية: {keyword}")
        # قياس الهيمنة
        self.dominance_score(keyword)

        # 1️⃣ العقل الأساسي: تغريدة الخبر
        main_prompt = f"اكتب خبر سكوب عن {keyword} بلهجة خليجية، ركز على فائدة الفرد."
        main_content = self._ask_ai(main_prompt)
        if not main_content: return

        content_hash = hashlib.md5(main_content.encode()).hexdigest()
        if self._is_posted(content_hash):
            logging.info("⚠️ المحتوى مكرر، تم الإيقاف.")
            return

        try:
            main_tweet = self.x_client.create_tweet(text=main_content)
            main_id = main_tweet.data["id"]
            self._mark_posted(content_hash, main_id, "main")
            logging.info("✅ تم نشر التغريدة الأساسية")

            # 2️⃣ العقل الثاني: جوك
            time.sleep(5)
            joke_prompt = f"استنادًا للخبر: '{main_content}'، أعطنا معلومة ممتعة/سريعة للأفراد بلهجة خليجية."
            joke_content = self._ask_ai(joke_prompt)
            if joke_content:
                joke_hash = hashlib.md5(joke_content.encode()).hexdigest()
                if not self._is_posted(joke_hash):
                    reply_1 = self.x_client.create_tweet(text=joke_content, in_reply_to_tweet_id=main_id)
                    self._mark_posted(joke_hash, reply_1.data["id"], "joke")
                    logging.info("✅ نشر رد العقل الثاني (جوك)")

            # 3️⃣ العقل الثالث: كوين
            time.sleep(5)
            coin_prompt = f"اقترح أداة ذكاء اصطناعي مرتبطة بـ {keyword} تساعد الفرد يوميًا، بلهجة خليجية."
            coin_content = self._ask_ai(coin_prompt)
            if coin_content:
                coin_hash = hashlib.md5(coin_content.encode()).hexdigest()
                if not self._is_posted(coin_hash):
                    self.x_client.create_tweet(
                        text=f"💡 أداة ننصحك تجربها:\n{coin_content}",
                        in_reply_to_tweet_id=reply_1.data["id"]
                    )
                    self._mark_posted(coin_hash, coin_content, "coin")
                    logging.info("✅ نشر رد العقل الثالث (كوين)")

        except Exception as e:
            if "429" in str(e):
                logging.error("🛑 خطأ 429: زحمة طلبات. خروج آمن.")
                sys.exit(0)
            logging.error(f"❌ فشل في تسلسل التغريدات: {e}")

    # === تشغيل الكلمات المفتاحية ===
    def run_targets(self, targets):
        self.monitor_competitors()
        for target in targets:
            self.process_and_post(target)
            logging.info("⏳ استراحة قصيرة بين الكلمات...")
            time.sleep(60)


if __name__ == "__main__":
    bot = SovereignBotV16()
    targets = ["مساعدات الذكاء الاصطناعي الشخصية", "أدوات الفيديو بالذكاء الاصطناعي"]
    bot.run_targets(targets)
