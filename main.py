import os
import sqlite3
import logging
import hashlib
import tweepy
import feedparser
from datetime import datetime, timezone
from google import genai
from openai import OpenAI

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignExpert:
    def __init__(self):
        # 1. تعريف مصفوفة المفاتيح حسب دستورك المعتمد
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "openrouter": os.getenv("OPENROUTER_API_KEY"),
            "xai": os.getenv("XAI_API_KEY"),
            "qwen": os.getenv("QWEN_API_KEY")
        }
        
        # 2. مفاتيح منصة X
        self.x_creds = {
            "api": os.getenv("X_API_KEY"),
            "secret": os.getenv("X_API_SECRET"),
            "token": os.getenv("X_ACCESS_TOKEN"),
            "t_secret": os.getenv("X_ACCESS_SECRET"),
            "bearer": os.getenv("X_BEARER_TOKEN")
        }

        self.db_path = "data/expert_v26.db"
        self._init_db()
        self._setup_x()
        self._setup_brains()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, url TEXT, ts DATETIME)")

    def _setup_x(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=self.x_creds["bearer"],
                consumer_key=self.x_creds["api"],
                consumer_secret=self.x_creds["secret"],
                access_token=self.x_creds["token"],
                access_token_secret=self.x_creds["t_secret"]
            )
            logging.info("✅ منصة X متصلة.")
        except Exception as e: logging.error(f"❌ خطأ X: {e}")

    def _setup_brains(self):
        """تهيئة العقول الستة بنظام الفحص الاستباقي"""
        self.brains = {}
        # Gemini
        if self.keys["gemini"]:
            self.brains["gemini"] = genai.Client(api_key=self.keys["gemini"])
        # OpenAI & Others (OpenAI-compatible protocol)
        configs = {
            "openai": (self.keys["openai"], None, "gpt-4o-mini"),
            "groq": (self.keys["groq"], "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
            "openrouter": (self.keys["openrouter"], "https://openrouter.ai/api/v1", "google/gemini-2.0-flash-001"),
            "xai": (self.keys["xai"], "https://api.x.ai/v1", "grok-beta"),
            "qwen": (self.keys["qwen"], "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-max")
        }
        
        for name, (key, url, model) in configs.items():
            if key:
                self.brains[name] = {"client": OpenAI(api_key=key, base_url=url), "model": model}
        
        logging.info(f"🧠 العقول الجاهزة للخدمة: {list(self.brains.keys())}")

    def generate_content(self, prompt):
        """محرك التبديل التلقائي السلس"""
        order = ["gemini", "openai", "groq", "xai", "openrouter", "qwen"]
        
        for name in order:
            if name not in self.brains: continue
            try:
                logging.info(f"🔄 محاولة الاستعانة بـ: {name}")
                if name == "gemini":
                    res = self.brains[name].models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    return res.text.strip()
                else:
                    res = self.brains[name]["client"].chat.completions.create(
                        model=self.brains[name]["model"],
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return res.choices[0].message.content.strip()
            except Exception as e:
                logging.warning(f"⚠️ {name} اعتذر عن الخدمة (نفاذ حصة أو ضغط). ننتقل للتالي...")
                continue
        return None

    def run(self):
        # جلب الأخبار
        feed = feedparser.parse("https://techcrunch.com/category/artificial-intelligence/feed/")
        for entry in feed.entries[:5]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    prompt = f"صغ هذا الخبر بلهجة خليجية بيضاء كخبير تقني، ركز على أدوات الذكاء الاصطناعي للأفراد: {entry.title}. المصدر: {entry.link}"
                    final_text = self.generate_content(prompt)
                    
                    if final_text:
                        self.x_client.create_tweet(text=final_text[:278])
                        conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                        conn.commit()
                        logging.info(f"🚀 تم النشر بنجاح عبر نظام العقول المتعددة!")
                        break # نشر تغريدة واحدة في كل دورة

if __name__ == "__main__":
    SovereignExpert().run()
