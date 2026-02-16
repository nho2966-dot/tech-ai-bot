import os
import csv
import logging
import sqlite3
import random
import uuid
import re
import requests
import feedparser
import tweepy
from datetime import datetime
from google import genai

# === إعداد اللوج السيادي ===
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")
logger = logging.getLogger("SovereignBot")

# === وظائف التنظيف والتأخير ===
def clean_text(text):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()

def apply_delay(min_sec=30, max_sec=60):
    wait = random.randint(min_sec, max_sec)
    logger.info(f"⏳ انتظار سيادي {wait} ثانية...")
    time_sleep(wait)

def time_sleep(seconds):
    import time
    time.sleep(seconds)

# === نظام إدارة المحركات والتقارير ===
def log_event(prompt, response, engine):
    filename = "bot_log.csv"
    fieldnames = ["datetime", "engine", "prompt", "response"]
    exists = os.path.isfile(filename)
    with open(filename, mode='a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists: writer.writeheader()
        writer.writerow({
            "datetime": datetime.now().isoformat(),
            "engine": engine,
            "prompt": prompt[:50],
            "response": response[:50]
        })

def send_telegram(message):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
        except Exception as e:
            logger.error(f"⚠️ خطأ تلجرام: {e}")

# === بوت السيادة الرقمية ===
class SovereignBot:
    def __init__(self):
        self.db_path = "sovereign_memory.db"
        self._init_db()
        
        # تهيئة عملاء X (API v1.1 للصور و v2 للنصوص)
        try:
            auth = tweepy.OAuth1UserHandler(
                os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
                os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
            )
            self.api_v1 = tweepy.API(auth)
            self.client_v2 = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة عملاء X: {e}")

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (content_hash TEXT PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS processed_mentions (mention_id TEXT PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def generate_ai_content(self, prompt, is_reply=False):
        # مصفوفة المحركات المتاحة
        engines = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY") # يمكن إضافة البقية هنا بنفس الطريقة
        }
        available = {k: v for k, v in engines.items() if v}
        if not available: return None

        engine_name = random.choice(list(available.keys()))
        sys_instruction = (
            "أنت خبير تقني خليجي متمكن. ركز حصراً على Artificial Intelligence and its latest tools "
            "التي تخدم الأفراد وتطور حياتهم. اللهجة: خليجية بيضاء راقية. "
            "استبدل 'الثورة الصناعية' بـ 'Artificial Intelligence and its latest tools'."
        )

        try:
            # هنا نستخدم Gemini كمحرك أساسي
            client = genai.Client(api_key=available[engine_name])
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'system_instruction': sys_instruction}
            )
            res_text = response.text.strip()
            log_event(prompt, res_text, engine_name)
            return res_text
        except Exception as e:
            logger.error(f"❌ فشل محرك {engine_name}: {e}")
            return None

    def download_image(self, url):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                filename = f"temp_{uuid.uuid4().hex}.jpg"
                with open(filename, "wb") as f:
                    f.write(response.content)
                return filename
        except: return None

    def run_automation(self):
        """الدورة الآلية بالكامل بدون أي مدخلات يدوية"""
        logger.info("🚀 بدء المهمة الآلية...")
        
        # 1. جلب الأخبار من الـ RSS
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        posted = 0
        for entry in feed.entries:
            if posted >= 2: break # نكتفي بتغريدتين لكل دورة
            
            content_hash = str(hash(entry.title + entry.link))
            with sqlite3.connect(self.db_path) as conn:
                if conn.execute("SELECT content_hash FROM history WHERE content_hash = ?", (content_hash,)).fetchone():
                    continue

            # استخراج صورة إن وجدت
            img_url = entry.media_content[0]['url'] if 'media_content' in entry else None
            
            content = self.generate_ai_content(f"لخص هذا الخبر للأفراد بلهجة خليجية: {clean_text(entry.title)}")
            if content:
                media_ids = []
                img_path = self.download_image(img_url) if img_url else None
                if img_path:
                    try:
                        media = self.api_v1.media_upload(filename=img_path)
                        media_ids = [media.media_id]
                        os.remove(img_path)
                    except: pass

                try:
                    apply_delay(40, 80)
                    self.client_v2.create_tweet(text=content, media_ids=media_ids if media_ids else None)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (content_hash) VALUES (?)", (content_hash,))
                    send_telegram(f"✅ تم نشر تغريدة: {content[:50]}...")
                    posted += 1
                except Exception as e:
                    logger.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    bot = SovereignBot()
    bot.run_automation()
