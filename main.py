import os
import sqlite3
import feedparser
import tweepy
import time
import random
import sys
from datetime import datetime
from google import genai

# إعداد اللوج ليكون واضحاً في GitHub Actions
import logging
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
logger = logging.getLogger("SovereignBot")

class SovereignBot:
    def __init__(self):
        # إعداد المسارات وقاعدة البيانات (الكوين)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.base_dir, "data", "bot_v3.db")
        self._init_db()

        # الاتصال بجمناي (العقل)
        self.gemini_key = os.getenv("GEMINI_KEY")
        self.sys_instruction = (
            "Focus on Artificial Intelligence and its latest tools for individuals, with a Gulf dialect. "
            "Professional, accurate. Replace 'Industrial Revolution' with 'Artificial Intelligence and its latest tools'. "
            "Include contests, polls, and scoops. No Chinese, no symbols. Target individuals only."
        )

        # الاتصال بـ X (المنصة)
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            self.bot_id = self.x_client.get_me().data.id
            logger.info("✅ Connected to X successfully.")
        except Exception as e:
            logger.error(f"❌ Connection Error: {e}")
            sys.exit(1)

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, type TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS evergreen (tool TEXT, info TEXT)")

    def _generate_content(self, prompt):
        try:
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"⚠️ Gemini Error: {e}")
            return None

    def handle_mentions(self):
        """الرد على المتابعين ببطء لتجنب 429"""
        try:
            # جلب آخر 5 منشن فقط لتقليل الضغط
            mentions = self.x_client.get_users_mentions(self.bot_id, max_results=5)
            if not mentions.data: return

            for tweet in mentions.data:
                h = f"reply_{tweet.id}"
                if self._exists(h): continue

                reply = self._generate_content(f"رد بلهجة خليجية ذكية على: {tweet.text}")
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    self._mark(h, "reply")
                    logger.info(f"✅ Replied to tweet {tweet.id}")
                    time.sleep(40) # فاصل زمني أمان
        except Exception as e:
            if "429" in str(e):
                logger.warning("⚠️ 429 Hit in Mentions. Exiting to cool down.")
                sys.exit(0)

    def run_hierarchy_logic(self):
        """التسلسل الهرمي: Google -> Tech News -> Vault"""
        time.sleep(30) # راحة بين المهام
        
        # 1. المصادر الرسمية (الهرم)
        sources = [
            {'name': 'Google Gemini', 'url': 'https://blog.google/products/gemini/rss/'},
            {'name': 'TechCrunch AI', 'url': 'https://techcrunch.com/category/artificial-intelligence/feed/'}
        ]

        # اختيار نمط المحتوى لليوم
        content_mode = random.choice(['news', 'contest', 'scoop', 'poll'])

        for src in sources:
            feed = feedparser.parse(src['url'])
            if not feed.entries: continue
            
            for entry in feed.entries[:2]:
                h = str(hash(entry.title))
                if self._exists(h): continue

                prompt = self._build_special_prompt(content_mode, entry.title)
                content = self._generate_content(prompt)

                if self._post_tweet(content, h, content_mode):
                    return # نشرنا تغريدة واحدة بنجاح، ننهي الدورة

        # 2. الخيار البديل (الخزين/الكوين) في حال فشل المصادر
        self._post_from_vault()

    def _build_special_prompt(self, mode, title):
        if mode == 'contest': return f"سوي مسابقة سريعة (سؤال وخيارات) بناءً على الخبر: {title}. لهجة خليجية."
        if mode == 'scoop': return f"حلل الخبر بأسلوب 'سكوب صحفي' (تحليل عميق للفرد): {title}. لهجة خليجية."
        if mode == 'poll': return f"اكتب نص استطلاع رأي تفاعلي حول: {title}. لهجة خليجية."
        return f"اكتب منشور Premium طويل عن خبر: {title}. لهجة خليجية."

    def _post_tweet(self, text, h, c_type):
        if not text: return False
        try:
            self.x_client.create_tweet(text=text)
            self._mark(h, c_type)
            logger.info(f"✅ Posted {c_type} successfully.")
            return True
        except Exception as e:
            if "429" in str(e):
                logger.error("🛑 429 Rate Limit. Emergency Stop.")
                sys.exit(0)
            return False

    def _post_from_vault(self):
        """المستوى الأخير في الهرم: الخزين"""
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT tool, info FROM evergreen ORDER BY RANDOM() LIMIT 1").fetchone()
            if res:
                h = f"vault_{hash(res[0])}"
                if not self._exists(h):
                    content = self._generate_content(f"منشور إبداعي عن أداة AI: {res[0]} - {res[1]}")
                    self._post_tweet(content, h, "evergreen")

    def _exists(self, h):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone() is not None

    def _mark(self, h, c_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (hash, type) VALUES (?, ?)", (h, c_type))

if __name__ == "__main__":
    bot = SovereignBot()
    # الترتيب: ردود أولاً، ثم خبر واحد دسم
    bot.handle_mentions()
    bot.run_hierarchy_logic()
