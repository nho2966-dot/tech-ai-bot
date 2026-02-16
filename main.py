import os
import yaml
import sqlite3
import logging
import time
import feedparser
import tweepy
import re
from datetime import datetime, timedelta, timezone
from google import genai

# -------------------------
# 1. نظام التحميل واللوج السيادي
# -------------------------
def load_config():
    """تحميل الإعدادات من المسار المحدد utils/config.yaml"""
    config_path = os.path.join("utils", "config.yaml")
    if not os.path.exists(config_path):
        config_path = "config.yaml"
    
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
# 2. كلاس البوت السيادي المطور
# -------------------------
class SovereignBot:
    def __init__(self):
        self.db_path = config['bot']['database_path']
        self._init_db()
        
        # تهيئة عميل X (Twitter) 
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
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history 
                (hash TEXT PRIMARY KEY, title TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)
            """)

    def is_sleep_time(self):
        """الالتزام بتوقيت الخليج المحلي (GMT+4) بدلاً من توقيت السيرفر"""
        # ضبط التوقيت على توقيت عمان/الإمارات (GMT+4)
        gulf_tz = timezone(timedelta(hours=4))
        now_gulf = datetime.now(gulf_tz)
        current_hour = now_gulf.hour
        
        start = config['bot']['sleep_start']
        end = config['bot']['sleep_end']
        
        logger.info(f"🕒 الوقت الحالي بتوقيت الخليج: {now_gulf.strftime('%H:%M')}")
        
        # منطق فحص النوم (يتعامل مع عبور منتصف الليل)
        if start < end:
            is_sleep = start <= current_hour < end
        else: 
            is_sleep = current_hour >= start or current_hour < end
            
        return is_sleep

    def clean_text(self, text):
        return re.sub(r'<.*?>', '', text).strip()

    def generate_ai_content(self, mode, context):
        """توليد محتوى سيادي يخدم المواطن العربي بلهجة خليجية"""
        sys_core = config['prompts']['system_core'].replace(
            "الثورة الصناعية", "Artificial Intelligence and its latest tools"
        )
        
        raw_prompt = config['prompts']['modes'].get(mode, config['prompts']['modes']['POST_FAST'])
        # تعديل البرومبت لدمج الهوية العربية والخليجية
        hybrid_prompt = (
            f"حلل هذا الخبر: {context}. "
            f"صغ لي تغريدة {raw_prompt} بلهجة خليجية بيضاء راقية. "
            "ركز على الفائدة المباشرة للمواطن العربي، وتجنب أخبار الشركات تماماً. "
            "استخدم مصطلحات تقنية بين قوسين عند الحاجة."
        )

        try:
            ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=hybrid_prompt,
                config={'system_instruction': sys_core}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ فشل توليد المحتوى: {e}")
            return None

    def run_mission(self):
        # فحص النوم أولاً
        if self.is_sleep_time():
            logger.info("🌙 البوت في وضع النوم (Sleep Mode) حسب توقيت الخليج المحلي.")
            return

        logger.info("📡 جلب كوكتيل الأخبار (عالمي + عربي)...")
        
        # دمج المصادر من config مع مصادر عربية إضافية
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
        for entry in all_entries:
            if posted_count >= 1: break # تغريدة واحدة في كل تشغيل للأكشن
            
            clean_title = self.clean_text(entry.title)
            content_hash = str(hash(clean_title))

            with sqlite3.connect(self.db_path) as conn:
                if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone():
                    continue

            # توليد المحتوى
            tweet_text = self.generate_ai_content("POST_FAST", clean_title)
            
            if tweet_text:
                try:
                    # إضافة لمسة نهائية
                    final_post = f"{tweet_text}\n\n#AI #تقنية #الذكاء_الاصطناعي"
                    
                    self.client.create_tweet(text=final_post)
                    
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (hash, title) VALUES (?, ?)", 
                                     (content_hash, clean_title))
                    
                    logger.info(f"✅ تم النشر بنجاح: {clean_title[:50]}...")
                    posted_count += 1
                except Exception as e:
                    logger.error(f"❌ خطأ في النشر على X: {e}")

# -------------------------
# 3. التشغيل التنفيذي
# -------------------------
if __name__ == "__main__":
    bot = SovereignBot()
    bot.run_mission()
