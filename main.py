import os
import yaml
import sqlite3
import logging
import time
import feedparser
import tweepy
import random
from datetime import datetime, timedelta, timezone
from google import genai

# 1. إعداد اللوج (التركيز على العمليات الناجحة والتحذيرات)
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
logger = logging.getLogger("SovereignBot")

class SovereignBot:
    def __init__(self):
        # إعداد المسارات المطلقة لضمان الوصول للملفات في GitHub Actions
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.base_dir, "data", "bot_sovereign.db")
        self._init_db()
        
        # الاتصال بالذكاء الاصطناعي (العقل: جمناي)
        self.gemini_key = os.getenv("GEMINI_KEY")
        self.sys_instruction = (
            "Focus on Artificial Intelligence and its latest tools for individuals, with a Gulf dialect. "
            "Professional, accurate, no hallucinations. Replace 'Industrial Revolution' with "
            "'Artificial Intelligence and its latest tools'. Include contests, polls, and journalistic scoops. "
            "Avoid Chinese and symbols. Source: Google Products."
        )

        # الاتصال بـ X (المنصة) مع معالجة 429 تلقائياً
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True # الحل الجذري الأول لـ 429
            )
            self.bot_id = self.x_client.get_me().data.id
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ X: {e}")
            self.bot_id = None

    def _init_db(self):
        """إنشاء الكوين (قاعدة البيانات) لضمان حفظ الذاكرة"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, type TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS evergreen (id INTEGER PRIMARY KEY, tool TEXT, info TEXT)")

    def ai_generate(self, prompt):
        """توليد المحتوى عبر جمناي"""
        try:
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return response.text.strip()
        except: return None

    def handle_mentions(self):
        """الردود الذكية مع حماية 429"""
        if not self.bot_id: return
        try:
            mentions = self.x_client.get_users_mentions(self.bot_id)
            if not mentions.data: return
            for tweet in mentions.data:
                h = f"reply_{tweet.id}"
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): continue
                
                reply = self.ai_generate(f"رد بلهجة خليجية ذكية على: {tweet.text}")
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    self._mark_as_published(h, "reply")
                    time.sleep(5) # فاصل زمني بسيط
        except Exception as e:
            if "429" in str(e): logger.warning("⚠️ 429 في المنشن.. تخطي.")

    def run_hierarchy_publisher(self):
        """التسلسل الهرمي (جوجل -> تيك كرانش -> الخزين)"""
        sources = [
            {'name': 'Google Gemini', 'url': 'https://blog.google/products/gemini/rss/'},
            {'name': 'Tech AI', 'url': 'https://techcrunch.com/category/artificial-intelligence/feed/'}
        ]

        # اختيار النوع: خبر، مسابقة، أو سكوب
        content_type = random.choice(['news', 'contest', 'scoop', 'poll'])
        
        for src in sources:
            feed = feedparser.parse(src['url'])
            for entry in feed.entries[:3]:
                h = str(hash(entry.title))
                if self._is_already_published(h): continue

                prompt = self._build_prompt(content_type, entry.title)
                content = self.ai_generate(prompt)
                
                if self._post_to_x(content, h, content_type):
                    return # نشرنا بنجاح، ننهي الدورة

        # المستوى الأخير (الخزين): إذا لم نجد خبر جديد
        self._publish_from_vault()

    def _build_prompt(self, c_type, title):
        prompts = {
            'news': f"اكتب منشور Premium طويل عن خبر: {title}. لهجة خليجية.",
            'contest': f"صمم مسابقة تفاعلية بناءً على خبر: {title}. سؤال وخيارات.",
            'scoop': f"بأسلوب صحفي (Scoop)، حلل خبر: {title}. ما وراء الخبر للفرد الخليجي؟",
            'poll': f"اكتب نص استطلاع رأي (Poll) تفاعلي حول موضوع: {title}."
        }
        return prompts.get(c_type, prompts['news'])

    def _post_to_x(self, text, h, c_type):
        if not text: return False
        try:
            self.x_client.create_tweet(text=text)
            self._mark_as_published(h, c_type)
            logger.info(f"✅ تم نشر {c_type} بنجاح.")
            return True
        except Exception as e:
            if "429" in str(e):
                logger.error("🛑 خطأ 429: توقف النشر حالياً للحماية.")
                time.sleep(600) # انتظار 10 دقائق لو انضربنا بـ 429
            return False

    def _is_already_published(self, h):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone() is not None

    def _mark_as_published(self, h, c_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (hash, type) VALUES (?, ?)", (h, c_type))

    def _publish_from_vault(self):
        """المستوى الثالث: الخزين"""
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT tool, info FROM evergreen ORDER BY RANDOM() LIMIT 1").fetchone()
            if res:
                h = f"vault_{hash(res[0])}"
                if not self._is_already_published(h):
                    content = self.ai_generate(f"أعد صياغة أداة من الخزين: {res[0]} - {res[1]}")
                    self._post_to_x(content, h, "evergreen")

if __name__ == "__main__":
    bot = SovereignBot()
    # 1. ردود
    bot.handle_mentions()
    # 2. نشر هرمي
    bot.run_hierarchy_publisher()
