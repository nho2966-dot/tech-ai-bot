import os
import time
import random
import sqlite3
import logging
import hashlib
import re
from datetime import datetime
import tweepy
import requests
from google import genai
from openai import OpenAI

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format="🛡️ [APEX MEDIA]: %(message)s")

# --- 1️⃣ الإعدادات الاستراتيجية للهوية والمعمارية ---
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

class ApexMediaSystem:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()
        self._init_clients()
        self.tech_keywords = ["ai", "iphone", "android", "openai", "google", "chip", "gpu", "update", "chatgpt"]
        self.angles = ["شرح مبسط للمستخدم", "تحليل تقني عميق", "تحذير أمني", "زاوية خفية", "توقع مستقبلي"]

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history(hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS performance(id TEXT PRIMARY KEY, category TEXT, likes INTEGER, replies INTEGER, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS trend_memory(keyword TEXT PRIMARY KEY, score INTEGER, last_seen DATETIME)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # --- 2️⃣ محرك التوليد بسلسلة التراجع (Fallback Chain) ---
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

    def generate_content(self, prompt):
        chain = [PRIMARY_PROVIDER] + FALLBACK_ORDER
        for provider in chain:
            try:
                logging.info(f"🧠 محاولة عبر: {provider}")
                text = self.call_specific_provider(provider, prompt)
                clean_text = re.sub(r'[\*\#\_\[\]\(\)\~\`\>]', '', text).strip()
                if len(clean_text) > 30:
                    logging.info(f"✅ نجاح من {provider}")
                    return clean_text[:MAX_TWEET_LENGTH]
            except Exception as e:
                logging.warning(f"❌ فشل {provider}: {str(e)[:40]}")
                continue
        return "تدري؟ تحديث أنظمة جوالك أول بأول هو خط الدفاع الأول عن خصوصيتك الرقمية."

    # --- 3️⃣ إدارة المحتوى والذكاء التشغيلي ---
    def detect_gap(self):
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT keyword FROM trend_memory ORDER BY score DESC LIMIT 1").fetchone()
        return row[0] if row else random.choice(self.tech_keywords)

    def run(self):
        topic = self.detect_gap()
        angle = random.choice(self.angles)
        
        prompt = f"أنت خبير تقني خليجي. اكتب تغريدة احترافية. الزاوية: {angle}. الموضوع: {topic}. بدون رموز أو نجوم."
        
        content = self.generate_content(prompt)
        
        # التأكد من عدم التكرار
        h = hashlib.sha256(content.encode()).hexdigest()
        with sqlite3.connect(DB_PATH) as conn:
            if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                logging.info("⚠️ المحتوى مكرر، إلغاء النشر.")
                return

            try:
                res = self.x_client.create_tweet(text=content)
                if res:
                    conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.utcnow()))
                    logging.info(f"🚀 تم النشر بنجاح: {content[:50]}...")
            except Exception as e:
                logging.error(f"❌ فشل النشر في X: {e}")

if __name__ == "__main__":
    system = ApexMediaSystem()
    system.run()
