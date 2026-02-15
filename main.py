import os
import time
import random
import hashlib
import yaml
import sqlite3
import logging
from datetime import datetime
import feedparser
import tweepy
import google.generativeai as genai
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# -------------------------
# إعداد اللوج (Logging)
# -------------------------
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger("SovereignBot")

# -------------------------
# تحميل الإعدادات
# -------------------------
def load_config():
    with open("utils/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

cfg = load_config()

# -------------------------
# إعداد X Client و Gemini
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
    conn = sqlite3.connect("data/sovereign.db", timeout=20)
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

def is_duplicate(content):
    content_hash = hashlib.md5(content.encode()).hexdigest()
    conn, cursor = get_db_conn()
    cursor.execute("SELECT 1 FROM history WHERE hash=?", (content_hash,))
    exists = cursor.fetchone() is not None
    if not exists:
        cursor.execute("INSERT INTO history (hash, content) VALUES (?,?)", (content_hash, content))
        conn.commit()
    conn.close()
    return exists

# -------------------------
# جلب الأخبار الحديثة
# -------------------------
TECH_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.engadget.com/rss.xml",
    "https://www.gsmarena.com/rss-news-releases.php"
]

def fetch_latest_news(limit=5):
    news_items = []
    for feed_url in TECH_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit]:
            title = entry.title
            link = entry.link
            summary = entry.get("summary", "")
            news_items.append(f"{title}\n{summary}\n{link}")
    return news_items

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

def get_ai_response(prompt):
    response = call_gemini_model(prompt)
    if not response:
        unique_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
        response = f"السيادة الرقمية للفرد هي المستقبل. [{unique_id}]"
    return response[:280]

def ai_tweet_from_news(news_text):
    prompt = f"{cfg['prompts']['system_core']}\n\nحول هذا الخبر إلى تغريدة ذكية قصيرة: {news_text}"
    return get_ai_response(prompt)

# -------------------------
# المهام التشغيلية
# -------------------------
def dispatch_tweet_with_content(content):
    if is_duplicate(content):
        logger.info("🚫 Duplicate content detected. Skipping...")
        return
    today = datetime.now().date().isoformat()
    count = int(get_meta(f"count_{today}", "0"))
    if count >= cfg['bot'].get('daily_tweet_limit', 40):
        logger.info("🚫 Daily limit reached.")
        return
    try:
        x_client.create_tweet(text=content)
        update_meta(f"count_{today}", str(count + 1))
        logger.info(f"🚀 Tweet Dispatched: {content[:50]}...")
    except Exception as e:
        logger.error(f"❌ D
