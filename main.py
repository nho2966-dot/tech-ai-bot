import os
import time
import random
import hashlib
import yaml
import sqlite3
import logging
from datetime import datetime

# المكتبات الأساسية
import tweepy
import google.generativeai as genai
from dotenv import load_dotenv

# تحميل المتغيرات من البيئة
load_dotenv()

# -------------------------
# إعداد اللوج (Logging)
# -------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("SovereignBot")

# -------------------------
# تحميل الإعدادات وتجهيز البيئة
# -------------------------
def load_config():
    with open("utils/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

cfg = load_config()

# -------------------------
# إعداد الاتصالات (X & Gemini)
# -------------------------
x_client = tweepy.Client(
    bearer_token=os.getenv("X_BEARER_TOKEN"),
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# -------------------------
# إدارة قاعدة البيانات
# -------------------------
def get_db_conn():
    conn = sqlite3.connect(cfg['bot']['database_path'], timeout=20)
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

def record_history(content):
    h = hashlib.md5(content.encode()).hexdigest()
    conn, cursor = get_db_conn()
    cursor.execute("INSERT OR IGNORE INTO history (hash, content) VALUES (?,?)", (h, content))
    conn.commit()
    conn.close()
    return h

def is_duplicate(content):
    h = hashlib.md5(content.encode()).hexdigest()
    conn, cursor = get_db_conn()
    cursor.execute("SELECT 1 FROM history WHERE hash=?", (h,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# -------------------------
# محركات الذكاء الاصطناعي
# -------------------------
def call_gemini_model(prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_prompt = f"{cfg['prompts']['system_core']}\n\nالسياق: {prompt}"
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"♊ Gemini Error: {e}")
        return None

def call_grok_logic(prompt):
    prompt = f"تقمص دور Grok، كن ساخراً وذكياً حول هذا الموضوع: {prompt}"
    return call_gemini_model(prompt)

def get_ai_response(prompt):
    response = call_gemini_model(prompt)
    if not response:
        response = call_grok_logic(prompt)
    if not response:
        unique_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
        response = f"السيادة الرقمية في الثورة الصناعية الرابعة مفتاح تمكين الفرد. [{unique_id}]"
    return response[:280]

# -------------------------
# التعامل مع الترندات اللحظية
# -------------------------
def fetch_trending_topics():
    try:
        trends = x_client.get_place_trends(id=1)  # WOEID عالمي
        topics = [t["name"] for t in trends[0]["trends"]]
        return topics[:10]
    except Exception as e:
        logger.error(f"⚠️ Fetch Trending Error: {e}")
        return []

def generate_trend_tweet():
    topics = fetch_trending_topics()
    if not topics:
        return None
    topic = random.choice(topics)
    prompt = f"حلل هذا الترند الحديث بعناية وقدم محتوى تقني أصيل (AI، الأجهزة، التسريبات، الهندسة الاجتماعية): {topic}"
    tweet = get_ai_response(prompt)
    if is_duplicate(tweet):
        logger.info("⚠️ Duplicate trend content skipped.")
        return None
    return tweet

def dispatch_trend_tweet():
    today = datetime.now().date().isoformat()
    count = int(get_meta(f"count_{today}", "0"))
    if count >= cfg['bot'].get('daily_tweet_limit', 40):
        logger.info("🚫 Daily tweet limit reached.")
        return
    tweet = generate_trend_tweet()
    if not tweet:
        return
    try:
        x_client.create_tweet(text=tweet)
        record_history(tweet)
        update_meta(f"count_{today}", str(count + 1))
        logger.info(f"🚀 Trend Tweet Dispatched: {tweet[:50]}...")
    except Exception as e:
        logger.error(f"❌ Trend Dispatch Failed: {e}")

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
            reply_text = get_ai_response(f"رد ذكي ومختصر على: {mention.text}")
            if not is_duplicate(reply_text):
                x_client.create_tweet(text=reply_text, in_reply_to_tweet_id=mention.id)
                cursor.execute("INSERT INTO replies (tweet_id, hash) VALUES (?,?)",
                               (str(mention.id), hashlib.md5(reply_text.encode()).hexdigest()))
                record_history(reply_text)
                logger.info(f"💬 Replied to: {mention.id}")
                time.sleep(random.uniform(5, 15))
        conn.commit()
        conn.close()
        if mentions.data:
            update_meta("last_mention_id", str(mentions.data[0].id))
    except Exception as e:
        logger.error(f"⚠️ Smart Replies Error: {e}")

# -------------------------
# التغريد اليومي العادي
# -------------------------
def dispatch_tweet():
    today = datetime.now().date().isoformat()
    count = int(get_meta(f"count_{today}", "0"))
    if count >= cfg['bot'].get('daily_tweet_limit', 40):
        logger.info("🚫 Daily limit reached.")
        return
    prompts = [
        "حلل كيف يمكن للذكاء الاصطناعي تعزيز سيادة الفرد الرقمية اليوم؟",
        "تحدث عن أداة تقنية من أدوات الثورة الصناعية الرابعة تفيد المستقلين.",
        "ما هو أثر البلوكشين على الخصوصية الشخصية في 2026؟",
        "أحدث الأجهزة الذكية ومقارناتها وأسرارها التقنية.",
        "الهندسة الاجتماعية وأهم طرق حماية الفرد في الفضاء الرقمي."
    ]
    content = get_ai_response(random.choice(prompts))
    if is_duplicate(content):
        logger.info("⚠️ Duplicate regular content skipped.")
        return
    try:
        x_client.create_tweet(text=content)
        record_history(content)
        update_meta(f"count_{today}", str(count + 1))
        logger.info(f"🚀 Strategic Tweet Dispatched: {content[:50]}...")
    except Exception as e:
        logger.error(f"❌ Dispatch Failed: {e}")

# -------------------------
# دورة التشغيل الأساسية
# -------------------------
def run_cycle():
    logger.info("⚙️ Sovereign Cycle Initiated...")
    hour = datetime.now().hour
    if cfg['bot']['sleep_start'] <= hour < cfg['bot']['sleep_end']:
        logger.info("💤 Bot is in sleep mode.")
        return
    dispatch_trend_tweet()  # التغريد حسب الترند
    dispatch_tweet()        # التغريد العادي
    smart_replies()         # الردود الذكية
    update_meta("last_run", str(time.time()))
    logger.info("🏁 Cycle Completed.")

if __name__ == "__main__":
    run_cycle()
