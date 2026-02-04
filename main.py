import os, sqlite3, logging, hashlib, time, re, random, json
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات المؤسسية ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class TechEliteEnterpriseSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # أوقات الذروة المستهدفة (بتوقيتك المحلي)
        self.peak_hours = [8, 9, 12, 13, 18, 19, 21, 22] 

    def _init_db(self):
        with sqlite3.connect("news_enterprise_full_2026.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS editorial_memory (content_hash TEXT PRIMARY KEY, summary TEXT, created_at TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, keywords TEXT)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_peak_time(self):
        """التحقق مما إذا كان الوقت الحالي مناسباً للنشر لرفع الـ ROI"""
        current_hour = datetime.now().hour
        is_peak = current_hour in self.peak_hours
        if not is_peak:
            logging.info(f"⏳ Current hour ({current_hour}) is not peak time. Skipping major posts...")
        return is_peak

    def _generate_ai(self, system_p, user_p, h):
        models = ["qwen/qwen-2.5-72b-instruct", "google/gemini-flash-1.5", "openai/gpt-4o-mini"]
        for model_name in models:
            try:
                r = self.ai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_p}, {"role": "user", "content": user_p}],
                    temperature=0.3, timeout=45
                )
                content = r.choices[0].message.content
                with sqlite3.connect("news_enterprise_full_2026.db") as conn:
                    conn.execute("INSERT OR IGNORE INTO editorial_memory VALUES (?, ?, ?)", (h, content[:50], datetime.now().isoformat()))
                return content
            except Exception as e:
                if "429" in str(e): continue
                logging.error(f"🚨 Model {model_name} failed: {e}")
        return None

    def run_cycle(self):
        logging.info("🚀 Sovereign Cycle Started")
        
        # 1. الردود الذكية تعمل دائماً لزيادة التفاعل العضوي
        self.process_smart_replies()
        
        # 2. النشر الاستهدافي (الثريدات) لا يتم إلا في أوقات الذروة
        if self._is_peak_time():
            self.execute_targeted_publishing()
        
        logging.info("🏁 Cycle Finished")

    # (بقية الدوال: process_smart_replies, execute_targeted_publishing, إلخ... كما في الكود السابق)
