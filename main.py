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

# 1. إعدادات اللوج والبيئة
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("SovereignBot")

def load_config():
    config_path = os.path.join("utils", "config.yaml")
    if not os.path.exists(config_path): config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# 2. كلاس إدارة المحتوى والذكاء الاصطناعي
class ContentEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_KEY")
        self.sys_instruction = config['prompts']['system_core'].replace(
            "الثورة الصناعية", "Artificial Intelligence and its latest tools"
        )

    def try_gemini(self, context, attempt=1):
        """المحرك الأول: Gemini مع Retry ذكي"""
        if attempt > 3: return None
        try:
            client = genai.Client(api_key=self.gemini_key)
            prompt = f"حلل تقنياً للفرد: {context}. صغ تغريدة خليجية بيضاء، ركز على الأدوات (tools)، استخدم مصطلحات إنجليزية بين قوسين، وتجنب أخبار الشركات."
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"⚠️ محاولة Gemini رقم {attempt} فشلت: {e}")
            time.sleep(5) # انتظار بسيط قبل الإعادة
            return self.try_gemini(context, attempt + 1)

    def try_alternative(self, mode="JOKE"):
        """المحركات البديلة: Joke أو Coin عند فشل الذكاء الاصطناعي"""
        if mode == "JOKE":
            return "الذكاء الاصطناعي (AI) صار مثل الملح في الأكل، بكل مكان! بس الأهم تعرف كيف تستخدمه لصالحك مو بس تتابعه. 😎 #تقنية"
        return "تحديث تقني: تذكر دائماً أن أمن بياناتك (Data Privacy) يبدأ بوعيك بالأدوات التي تستخدمها. استثمر في عقلك! 💡 #AI"

# 3. البوت الأساسي
class SovereignBot:
    def __init__(self):
        self.db_path = config['bot']['database_path']
        self.engine = ContentEngine()
        self._init_db()
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def _init_db(self):
        if not os.path.exists(os.path.dirname(self.db_path)): os.makedirs(os.path.dirname(self.db_path))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def is_sleep_time(self):
        """التزام بتوقيت الخليج (GMT+4)"""
        gulf_tz = timezone(timedelta(hours=4))
        now_gulf = datetime.now(gulf_tz)
        logger.info(f"🕒 الوقت الحالي بتوقيت الخليج: {now_gulf.strftime('%H:%M')}")
        hour = now_gulf.hour
        start, end = config['bot']['sleep_start'], config['bot']['sleep_end']
        return start <= hour < end if start < end else (hour >= start or hour < end)

    def run(self):
        if self.is_sleep_time():
            logger.info("🌙 وضع النوم نشط. نراك قريباً.")
            return

        # جلب الأخبار
        feeds = [f['url'] for f in config['sources']['rss_feeds']]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                content_hash = str(hash(entry.title))
                
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone(): continue

                # نظام المحركات المتتابع (Gemini -> البديل)
                tweet_text = self.engine.try_gemini(entry.title)
                if not tweet_text:
                    logger.info("🔄 الانتقال للمحرك البديل (Joke/Coin)...")
                    tweet_text = self.engine.try_alternative()

                if tweet_text:
                    try:
                        self.client.create_tweet(text=tweet_text[:280])
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute("INSERT INTO history (hash) VALUES (?)", (content_hash,))
                        logger.info(f"✅ تم النشر: {tweet_text[:50]}...")
                        return # نشر تغريدة واحدة في كل دورة
                    except Exception as e:
                        logger.error(f"❌ خطأ في X: {e}")

if __name__ == "__main__":
    SovereignBot().run()
