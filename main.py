import os
import yaml
import time
import sqlite3
import logging
import feedparser
import tweepy
from datetime import datetime
from google import genai # أو OpenAI حسب تفضيلك في الملف

# --- تحميل الإعدادات السيادية ---
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# --- إعداد اللوج بناءً على الملف ---
logging.basicConfig(
    level=config['logging']['level'],
    format="🛡️ %(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(config['logging']['name'])

class SovereignBot:
    def __init__(self):
        self.db_path = config['bot']['database_path']
        self._init_db()
        # تهيئة Tweepy (v2)
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def is_sleep_time(self):
        """الالتزام بتوقيت النوم السيادي المحدد في config"""
        now = datetime.now().hour
        start = config['bot']['sleep_start']
        end = config['bot']['sleep_end']
        return start <= now < end

    def generate_sovereign_content(self, prompt_type, context):
        """توليد محتوى يلتزم بالهوية والقواعد المذكورة في prompts"""
        # دمج التعليمات الأساسية مع نمط التغريدة
        sys_core = config['prompts']['system_core'].replace(
            "الثورة الصناعية", "Artificial Intelligence and its latest tools"
        )
        mode_prompt = config['prompts']['modes'][prompt_type].format(content=context)
        
        # استخدام المحرك المفضل (هنا مثال بـ Gemini كبديل أو GPT-4o حسب الربط)
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=mode_prompt,
            config={'system_instruction': sys_core}
        )
        return response.text.strip()

    def run_mission(self):
        if self.is_sleep_time():
            logger.info("🌙 البوت في وضع النوم السيادي حالياً...")
            return

        logger.info("🚀 بدء المهمة بناءً على قائمة المصادر والحسابات...")
        
        # 1. جلب الكوكتيل الإخباري (عالمي + عربي كما اتفقنا سابقاً)
        # سيتم استخدام الروابط من config['sources']['rss_feeds']
        for feed in config['sources']['rss_feeds']:
            entries = feedparser.parse(feed['url']).entries[:5]
            for entry in entries:
                content_hash = str(hash(entry.title))
                
                # فحص التكرار
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone():
                        continue
                
                # صياغة الخبر بنمط POST_FAST أو POST_DEEP
                tweet_text = self.generate_sovereign_content("POST_FAST", entry.title)
                
                try:
                    self.client.create_tweet(text=tweet_text)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (hash) VALUES (?)", (content_hash,))
                    logger.info(f"✅ تم النشر: {entry.title[:30]}")
                    break # الالتزام بحد التغريدات
                except Exception as e:
                    logger.error(f"❌ خطأ: {e}")

# --- التشغيل الآلي ---
if __name__ == "__main__":
    bot = SovereignBot()
    bot.run_mission()
