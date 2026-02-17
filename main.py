import os
import sqlite3
import logging
import time
import hashlib
import requests
import tweepy
import feedparser
from datetime import datetime, timezone
from google import genai
from openai import OpenAI

# إعداد السجلات لمراقبة أداء العقول
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignExpert:
    def __init__(self):
        # 1. ربط المفاتيح بالمسميات الدقيقة من صورتك
        self.secrets = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "xai": os.getenv("XAI_API_KEY"),
            # مفاتيح X
            "x_api": os.getenv("X_API_KEY"),
            "x_secret": os.getenv("X_API_SECRET"),
            "x_token": os.getenv("X_ACCESS_TOKEN"),
            "x_token_secret": os.getenv("X_ACCESS_SECRET"),
            "x_bearer": os.getenv("X_BEARER_TOKEN")
        }
        
        self.db_path = "data/expert_v28.db"
        self._init_db()
        self._setup_x()
        self._setup_brains()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, url TEXT, ts DATETIME)")

    def _setup_x(self):
        """الربط مع منصة X باستخدام المفاتيح المحفوظة"""
        try:
            self.x_client = tweepy.Client(
                bearer_token=self.secrets["x_bearer"],
                consumer_key=self.secrets["x_api"],
                consumer_secret=self.secrets["x_secret"],
                access_token=self.secrets["x_token"],
                access_token_secret=self.secrets["x_token_secret"]
            )
            logging.info("✅ نظام التواصل مع X متصل وجاهز.")
        except Exception as e:
            logging.error(f"❌ فشل ربط X: {e}")

    def _setup_brains(self):
        """تهيئة العقول المتاحة فقط بناءً على الـ Secrets"""
        self.active_brains = {}
        
        # العقل الأول: Gemini
        if self.secrets["gemini"]:
            self.active_brains["gemini"] = genai.Client(api_key=self.secrets["gemini"])
        
        # العقل الثاني: OpenAI
        if self.secrets["openai"]:
            self.active_brains["openai"] = OpenAI(api_key=self.secrets["openai"])
            
        # العقل الثالث: Groq
        if self.secrets["groq"]:
            self.active_brains["groq"] = OpenAI(api_key=self.secrets["groq"], base_url="https://api.groq.com/openai/v1")
            
        # العقل الرابع: XAI (Grok)
        if self.secrets["xai"]:
            self.active_brains["xai"] = OpenAI(api_key=self.secrets["xai"], base_url="https://api.x.ai/v1")

        logging.info(f"🧠 العقول التشغيلية: {list(self.active_brains.keys())}")

    def _ask_specific_brain(self, name, prompt):
        """تنفيذ الطلب حسب بروتوكول كل عقل"""
        if name == "gemini":
            res = self.active_brains[name].models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        
        # بقية العقول تستخدم بروتوكول OpenAI
        model_names = {"openai": "gpt-4o-mini", "groq": "llama-3.3-70b-versatile", "xai": "grok-beta"}
        res = self.active_brains[name].chat.completions.create(
            model=model_names[name],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return res.choices[0].message.content.strip()

    def failover_generator(self, prompt):
        """نظام التبديل الرباعي الذكي"""
        for brain_name in ["gemini", "openai", "groq", "xai"]:
            if brain_name in self.active_brains:
                try:
                    logging.info(f"🔄 محاولة مع العقل: {brain_name}")
                    result = self._ask_specific_brain(brain_name, prompt)
                    if result: return result
                except Exception as e:
                    logging.warning(f"⚠️ {brain_name} في حالة تعذر: {e}")
                    continue
        return None

    def fetch_latest_ai_tools(self):
        """جلب أخبار أدوات الذكاء الاصطناعي للأفراد"""
        feed_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:5]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR REPLACE INTO waiting_room VALUES (?, ?, ?, ?)",
                                (h, entry.title, entry.link, datetime.now(timezone.utc)))

    def run_cycle(self):
        self.fetch_latest_ai_tools()
        with sqlite3.connect(self.db_path) as conn:
            target = conn.execute("SELECT hash, content, url FROM waiting_room LIMIT 1").fetchone()
            if target:
                h, content, url = target
                # صياغة الطلب بلهجة خليجية بيضاء (AI Tools for Individuals)
                prompt = f"صغ هذا الخبر كخبير تقني خليجي متمكن. ركز على فوائد أدوات الذكاء الاصطناعي للأفراد. الخبر: {content}. الرابط: {url}"
                
                final_post = self.failover_generator(prompt)
                if final_post:
                    self.x_client.create_tweet(text=final_post[:278])
                    conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info("🚀 تم النشر بنجاح بفضل نظام العقول المتعددة!")

if __name__ == "__main__":
    expert = SovereignExpert()
    expert.run_cycle()
