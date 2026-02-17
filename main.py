import os
import sqlite3
import logging
import time
import hashlib
import requests
import tweepy
import feedparser
from io import BytesIO
from datetime import datetime, timezone

# استيراد مكتبات العقول
from google import genai
from openai import OpenAI
# ملاحظة: Groq و DeepSeek يستخدمون مكتبة OpenAI للربط بسهولة

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignExpert:
    def __init__(self):
        # تهيئة مفاتيح العقول من Secrets
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_KEY"),
            "groq": os.getenv("GROQ_KEY"),
            "deepseek": os.getenv("DEEPSEEK_KEY")
        }
        
        self.db_path = "data/expert_v26.db"
        self._init_db()
        self._setup_x()
        
        # تعريف عملاء العقول
        self.brain_gemini = genai.Client(api_key=self.keys["gemini"])
        self.brain_openai = OpenAI(api_key=self.keys["openai"])
        self.brain_groq = OpenAI(api_key=self.keys["groq"], base_url="https://api.groq.com/openai/v1")
        self.brain_deepseek = OpenAI(api_key=self.keys["deepseek"], base_url="https://api.deepseek.com")

    def _setup_x(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            logging.info("✅ تم ربط منصة X بنجاح.")
        except Exception as e: logging.error(f"❌ خطأ في ربط X: {e}")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, url TEXT, ts DATETIME)")

    def _ask_brain(self, brain_name, prompt):
        """وظيفة داخلية لكل عقل"""
        if brain_name == "gemini":
            res = self.brain_gemini.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        
        model_map = {
            "openai": "gpt-4o-mini",
            "groq": "llama-3.3-70b-versatile",
            "deepseek": "deepseek-chat"
        }
        client_map = {
            "openai": self.brain_openai,
            "groq": self.brain_groq,
            "deepseek": self.brain_deepseek
        }
        
        response = client_map[brain_name].chat.completions.create(
            model=model_map[brain_name],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()

    def generate_with_failover(self, prompt):
        """نظام الإدارة الرباعي: تبديل تلقائي عند الفشل أو نفاذ الحصة"""
        brains_order = ["gemini", "openai", "groq", "deepseek"]
        
        for brain in brains_order:
            try:
                logging.info(f"🧠 محاولة الصياغة باستخدام عقل: {brain}...")
                result = self._ask_brain(brain, prompt)
                if result:
                    logging.info(f"✅ نجح العقل {brain} في المهمة.")
                    return result
            except Exception as e:
                logging.warning(f"⚠️ العقل {brain} غير متاح حالياً (زحمة أو خطأ). ننتقل للتالي...")
                continue
        
        logging.error("❌ جميع العقول الأربعة فشلت في الاستجابة!")
        return None

    def handle_posting(self):
        # (دالة جلب الأخبار تبقى كما هي في النسخ السابقة)
        self.fetch_news()
        
        with sqlite3.connect(self.db_path) as conn:
            target = conn.execute("SELECT hash, content, url FROM waiting_room LIMIT 1").fetchone()
            if target:
                h, content, url = target
                prompt = f"اكتب تغريدة خليجية احترافية عن: {content}. المصدر: {url}"
                
                final_text = self.generate_with_failover(prompt)
                
                if final_text:
                    self.x_client.create_tweet(text=final_text[:280])
                    conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info("🚀 تم النشر بنجاح!")

    def fetch_news(self):
        # جلب الأخبار من RSS (نفس الكود السابق)
        feed = feedparser.parse("https://techcrunch.com/category/artificial-intelligence/feed/")
        for entry in feed.entries[:5]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR REPLACE INTO waiting_room VALUES (?, ?, ?, ?)",
                                (h, entry.title, entry.link, datetime.now(timezone.utc)))

if __name__ == "__main__":
    expert = SovereignExpert()
    expert.handle_posting()
