import os
import yaml
import sqlite3
import logging
import random
import time
import feedparser
import tweepy
from datetime import datetime
from google import genai

# -------------------------
# نظام التحميل واللوج السيادي
# -------------------------
def load_config():
    """تحميل الإعدادات من المسار المحدد utils/config.yaml"""
    config_path = os.path.join("utils", "config.yaml")
    if not os.path.exists(config_path):
        config_path = "config.yaml" # خيار احتياطي
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ خطأ فادح: تعذر العثور على ملف الإعدادات: {e}")
        raise

config = load_config()

logging.basicConfig(
    level=config['logging']['level'],
    format="🛡️ %(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(config['logging']['name'])

# -------------------------
# كلاس البوت السيادي المدمج
# -------------------------
class SovereignBot:
    def __init__(self):
        self.db_path = config['bot']['database_path']
        self._init_db()
        
        # تهيئة عميل X (Twitter) - الالتزام باشتراك X المدفوع
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            logger.info("✅ تم الاتصال بمنصة X بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في مفاتيح X API: {e}")

    def _init_db(self):
        """إنشاء مجلد البيانات وقاعدة البيانات إذا لم توجد"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history 
                (hash TEXT PRIMARY KEY, title TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)
            """)

    def is_sleep_time(self):
        """التوقف عن النشر في أوقات النوم المحددة في config"""
        now_hour = datetime.now().hour
        start = config['bot']['sleep_start']
        end = config['bot']['sleep_end']
        return start <= now_hour < end

    def clean_text(self, text):
        import re
        return re.sub(r'<.*?>', '', text).strip()

    def generate_ai_content(self, mode, context):
        """توليد محتوى ذكي يلتزم بالهوية السيادية المذكورة في البرومبت"""
        sys_core = config['prompts']['system_core'].replace(
            "الثورة الصناعية", "Artificial Intelligence and its latest tools"
        )
        
        # اختيار النمط من config
        raw_prompt = config['prompts']['modes'].get(mode, config['prompts']['modes']['POST_FAST'])
        final_prompt = raw_prompt.format(content=context)

        try:
            # استخدام Gemini كبديل ذكي وسريع
            ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=final_prompt,
                config={'system_instruction': sys_core}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ فشل توليد المحتوى عبر AI: {e}")
            return None

    def run_mission(self):
        if self.is_sleep_time():
            logger.info("🌙 البوت في وضع النوم (Sleep Mode) حسب الإعدادات.")
            return

        logger.info("📡 جلب الأخبار من المصادر العالمية والعربية (كوكتيل)...")
        
        # دمج المصادر من config مع مصادر عربية إضافية لضمان "الكوكتيل"
        rss_sources = [f['url'] for f in config['sources']['rss_feeds']]
        rss_sources.extend([
            "https://aitnews.com/category/artificial-intelligence/feed/",
            "https://www.tech-wd.com/wd/category/news/feed/"
        ])

        all_entries = []
        for url in rss_sources:
            try:
                feed = feedparser.parse(url)
                all_entries.extend(feed.entries[:5])
            except: continue

        # ترتيب حسب الأحدث
        all_entries.sort(key=lambda x: x.get('published_parsed', 0), reverse=True)

        posted_count = 0
        limit = config['bot']['daily_tweet_limit']

        for entry in all_entries:
            if posted_count >= 1: break # نشر تغريدة واحدة دسمة في كل دورة أكشن
            
            clean_title = self.clean_text(entry.title)
            content_hash = str(hash(clean_title))

            # فحص التكرار في sovereign.db
            with sqlite3.connect(self.db_path) as conn:
                if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone():
                    continue

            # توليد المحتوى بنمط POST_FAST أو POST_DEEP
            tweet_text = self.generate_ai_content("POST_FAST", clean_title)
            
            if tweet_text:
                try:
                    # إضافة الهاشتاقات المختارة بعناية للمواطن العربي
                    final_post = f"{tweet_text}\n\n#AI #تقنية #الذكاء_الاصطناعي"
                    
                    self.client.create_tweet(text=final_post)
                    
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (hash, title) VALUES (?, ?)", 
                                     (content_hash, clean_title))
                    
                    logger.info(f"✅ تم بنجاح نشر: {clean_title[:40]}...")
                    posted_count += 1
                except Exception as e:
                    logger.error(f"❌ فشل إرسال التغريدة: {e}")

# -------------------------
# التشغيل التنفيذي
# -------------------------
if __name__ == "__main__":
    bot = SovereignBot()
    bot.run_mission()
