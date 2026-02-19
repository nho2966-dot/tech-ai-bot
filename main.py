import os
import time
import random
import sqlite3
import logging
import hashlib
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import tweepy
from google import genai
from openai import OpenAI

# --- إعدادات التسجيل ---
logging.basicConfig(level=logging.INFO, format="🛡️ [APEX MEDIA]: %(message)s")

# --- 1️⃣ الإعدادات الاستراتيجية ---
PRIMARY_PROVIDER = "gemini"
FALLBACK_ORDER = ["groq", "openai", "xai"]

PROVIDERS = {
    "gemini": {"type": "google", "model": "gemini-1.5-flash", "env": "GEMINI_KEY"},
    "groq": {"type": "openai", "model": "llama-3.3-70b-versatile", "base_url": "https://api.groq.com/openai/v1", "env": "GROQ_API_KEY"},
    "openai": {"type": "openai", "model": "gpt-4o-mini", "env": "OPENAI_API_KEY"},
    "xai": {"type": "openai", "model": "grok-beta", "base_url": "https://api.x.ai/v1", "env": "XAI_API_KEY"}
}

DB_PATH = "data/apex_media.db"
MAX_TWEET_LENGTH = 280

# --- البوت الرئيسي ---
class ApexMediaSystem:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()
        self._init_clients()
        self.tech_keywords = ["ai", "iphone", "android", "openai", "google", "chip", "gpu", "update", "chatgpt"]
        self.angles = ["شرح مبسط", "تحليل تقني عميق", "تحذير أمني", "زاوية خفية", "توقع مستقبلي"]

    # --- قاعدة البيانات ---
    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history(hash TEXT PRIMARY KEY, content TEXT, source_url TEXT, ts DATETIME)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_ts ON history(ts)")
            conn.execute("CREATE TABLE IF NOT EXISTS performance(id TEXT PRIMARY KEY, category TEXT, likes INTEGER, replies INTEGER, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS trend_memory(keyword TEXT PRIMARY KEY, score INTEGER, last_seen DATETIME)")

    # --- تهيئة X API ---
    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # --- جلب المقال الكامل ---
    def fetch_full_article(self, url):
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = " ".join(p.get_text() for p in paragraphs)
            return text
        except Exception as e:
            logging.error(f"❌ فشل جلب المقال: {e}")
            return ""

    # --- محرك Fallback ---
    def call_specific_provider(self, p_key, prompt):
        cfg = PROVIDERS[p_key]
        api_key = os.getenv(cfg["env"])
        if not api_key: raise Exception(f"Key missing: {p_key}")

        if cfg["type"] == "google":
            client = genai.Client(api_key=api_key)
            res = client.models.generate_content(model=cfg["model"], contents=prompt)
            return res.text
        else:
            client = OpenAI(api_key=api_key, base_url=cfg.get("base_url"))
            res = client.chat.completions.create(
                model=cfg["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7, max_tokens=300
            )
            return res.choices[0].message.content

    # --- توليد التغريدة الاحترافية ---
    def generate_content(self, prompt):
        chain = [PRIMARY_PROVIDER] + FALLBACK_ORDER
        for idx, provider in enumerate(chain):
            try:
                logging.info(f"🧠 محاولة عبر: {provider}")
                text = self.call_specific_provider(provider, prompt)
                clean_text = re.sub(r'[^\w\s\p{Arabic}.,!?]', '', text, flags=re.UNICODE).strip()
                if len(clean_text) > 30:
                    logging.info(f"✅ نجاح من {provider}")
                    return clean_text[:MAX_TWEET_LENGTH]
            except Exception as e:
                logging.warning(f"❌ فشل {provider}: {str(e)[:60]} | محاولة {idx+1}/{len(chain)}")
                time.sleep(1 + idx*2)
                continue
        return "تحديث جوالك وحماية خصوصيتك خطوة أولى للحفاظ على بياناتك."

    # --- كشف الفجوات ---
    def detect_gap(self):
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT keyword FROM trend_memory ORDER BY score DESC LIMIT 1").fetchone()
        return row[0] if row else random.choice(self.tech_keywords)

    # --- التحقق من التكرار ---
    def is_duplicate(self, content):
        h_new = hashlib.sha256(content.encode()).hexdigest()
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT content FROM history").fetchall()
            for r in rows:
                if fuzz.ratio(content, r[0]) > 85:
                    return True, h_new
            return False, h_new

    # --- تحديث الأداء ---
    def log_performance(self, tweet_id, category, likes=0, replies=0):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO performance(id, category, likes, replies, ts) VALUES (?, ?, ?, ?, ?)",
                         (tweet_id, category, likes, replies, datetime.utcnow()))

    # --- توليد تغريدة من خبر + كشف خبايا ---
    def create_tweet_from_url(self, url):
        full_text = self.fetch_full_article(url)
        if not full_text:
            logging.warning("⚠️ لا يمكن قراءة المقال بالكامل")
            return

        angle = random.choice(self.angles)
        prompt = f"أنت خبير تقني. اقرأ المقال التالي بعناية واكتب تغريدة احترافية تكشف خفايا وأسرار التقنية والأجهزة الذكية والذكاء الاصطناعي. الزاوية: {angle}\n\n{full_text}"
        tweet_content = self.generate_content(prompt)

        is_dup, h = self.is_duplicate(tweet_content)
        if is_dup:
            logging.info("⚠️ المحتوى مكرر، إلغاء النشر.")
            return

        for attempt in range(3):
            try:
                res = self.x_client.create_tweet(text=tweet_content)
                if res:
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.execute("INSERT INTO history(hash, content, source_url, ts) VALUES (?, ?, ?, ?)",
                                     (h, tweet_content, url, datetime.utcnow()))
                    logging.info(f"🚀 تم النشر بنجاح: {tweet_content[:50]}...")
                    self.log_performance(res.data['id'], angle)
                    break
            except Exception as e:
                logging.error(f"❌ محاولة {attempt+1} فشل النشر: {e}")
                time.sleep(2)

# --- تشغيل البوت ---
if __name__ == "__main__":
    system = ApexMediaSystem()
    # مثال: ضع رابط خبر حقيقي
    news_url = "https://www.theverge.com/tech/ai-news"
    system.create_tweet_from_url(news_url)
