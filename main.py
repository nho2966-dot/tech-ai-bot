import os
import time
import random
import hashlib
import yaml
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# المكتبات الأساسية
import tweepy
import feedparser
import requests
from bs4 import BeautifulSoup
import google.genai as genai
from dotenv import load_dotenv

# تحميل المتغيرات من البيئة
load_dotenv()

# -------------------------
# إعداد اللوج
# -------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("SovereignBot")

# -------------------------
# تحميل الإعدادات
# -------------------------
CONFIG_PATH = Path("utils/config.yaml")
if not CONFIG_PATH.exists():
    logger.error("❌ config.yaml غير موجود!")
    exit(1)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

# -------------------------
# إعداد X Client (تويتر)
# -------------------------
x_client = tweepy.Client(
    bearer_token=os.getenv("X_BEARER_TOKEN"),
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

# -------------------------
# إعداد Gemini
# -------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# -------------------------
# إدارة قاعدة البيانات
# -------------------------
DB_PATH = cfg["bot"]["database_path"]

def get_db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, hash TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, content TEXT)")
    conn.commit()
    return conn, cursor

def get_meta(key, default=None):
    conn, cursor = get_db_conn()
    cursor.execute("SELECT value FROM meta WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def update_meta(key, value):
    conn, cursor = get_db_conn()
    cursor.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()

def has_been_posted(content_hash):
    conn, cursor = get_db_conn()
    cursor.execute("SELECT 1 FROM history WHERE hash=?", (content_hash,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def record_post(content):
    conn, cursor = get_db_conn()
    content_hash = hashlib.md5(content.encode()).hexdigest()
    cursor.execute("INSERT OR IGNORE INTO history (hash, content) VALUES (?,?)", (content_hash, content))
    conn.commit()
    conn.close()

# -------------------------
# الذكاء الاصطناعي
# -------------------------
def call_gemini(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        full_prompt = f"{cfg['prompts']['system_core']}\n\nالسياق: {prompt}"
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"♊ Gemini Error: {e}")
        return None

def get_ai_response(prompt):
    response = call_gemini(prompt)
    if not response:
        # fallback قصير
        unique_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
        response = f"السيادة الرقمية في الثورة الصناعية الرابعة مفتاح تمكين الفرد [{unique_id}]"
    # منع التكرار
    content_hash = hashlib.md5(response.encode()).hexdigest()
    if has_been_posted(content_hash):
        logger.warning("⚠️ تم اكتشاف محتوى مكرر، توليد بديل...")
        return get_ai_response(prompt + f" {random.randint(0,9999)}")
    record_post(response)
    return response[:280]

# -------------------------
# الردود الذكية
# -------------------------
def smart_replies():
    account_id = os.getenv("X_ACCOUNT_ID")
    last_id = get_meta("last_mention_id", "1")
    
    try:
        mentions = x_client.get_users_mentions(id=account_id, since_id=last_id)
        if not mentions.data:
            return

        conn, cursor = get_db_conn()
        for mention in reversed(mentions.data):
            cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(mention.id),))
            if cursor.fetchone(): continue

            reply_text = get_ai_response(f"رد ذكي على: {mention.text}")
            x_client.create_tweet(text=reply_text, in_reply_to_tweet_id=mention.id)

            cursor.execute("INSERT INTO replies (tweet_id, hash) VALUES (?,?)", 
                           (str(mention.id), hashlib.md5(reply_text.encode()).hexdigest()))
            logger.info(f"💬 Replied to: {mention.id}")
            time.sleep(random.uniform(5, 12))
        
        conn.commit()
        conn.close()
        update_meta("last_mention_id", str(mentions.data[0].id))
    except Exception as e:
        logger.error(f"⚠️ Smart Replies Error: {e}")

# -------------------------
# التغريدات اليومية
# -------------------------
TOPICS = [
    "حلل أحدث الأجهزة الذكية ومقارنة بين آخر الإصدارات",
    "اكتشف خبايا التقنية والتسريبات الموثوقة لهذا الشهر",
    "الهندسة الاجتماعية وأثرها على الأمان الرقمي للفرد",
    "استخدام الذكاء الاصطناعي لتعزيز الإنتاجية الفردية وأدواته",
    "مراجعة أحدث البرمجيات والأدوات التقنية",
    "تحديثات هامة في عالم البلوكشين والخصوصية الرقمية",
    "نصائح تقنية غير متوقعة تساعد المستقلين"
]

def dispatch_tweet():
    today = datetime.now().date().isoformat()
    count = int(get_meta(f"count_{today}", "0"))
    if count >= cfg['bot'].get("daily_tweet_limit", 40):
        logger.info("🚫 Daily limit reached.")
        return

    prompt = random.choice(TOPICS)
    content = get_ai_response(prompt)

    try:
        x_client.create_tweet(text=content)
        update_meta(f"count_{today}", str(count + 1))
        logger.info(f"🚀 Tweet sent: {content[:50]}...")
    except Exception as e:
        logger.error(f"❌ Dispatch Failed: {e}")

# -------------------------
# دورة التشغيل
# -------------------------
def run():
    logger.info("⚙️ SovereignBot Cycle Initiated")
    hour = datetime.now().hour
    if cfg['bot']['sleep_start'] <= hour < cfg['bot']['sleep_end']:
        logger.info("💤 Bot in sleep mode")
        return

    dispatch_tweet()
    smart_replies()
    update_meta("last_run", str(time.time()))
    logger.info("🏁 Cycle Completed")

if __name__ == "__main__":
    run()
