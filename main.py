import os
import sqlite3
import hashlib
import logging
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

import tweepy
from google import genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# إعدادات التسجيل الاحترافية
logging.basicConfig(level=logging.INFO, format="🛡️ [إمبراطورية ناصر]: %(message)s")

class NasserSovereignBot:
    def __init__(self):
        self.db_path = "data/sovereign_2026.db"
        self._init_db()
        self._setup_clients()
        # حدود النشر لمنع الإغراق (قوانين X)
        self.MAX_DAILY_POSTS = 4
        self.MIN_HOURS_BETWEEN_POSTS = 3

    def _init_db(self):
        """تجهيز قاعدة البيانات (الذاكرة التراكمية)"""
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS history 
                            (hash TEXT PRIMARY KEY, topic TEXT, content_type TEXT, 
                             ts DATETIME, analyzed INTEGER DEFAULT 0)""")

    def _setup_clients(self):
        """إعداد الاتصال بمنصات الذكاء الاصطناعي و X"""
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        # العقول المدبرة (Gemini 2.0 & Llama 3.3)
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.groq = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")

    # --- محرك الذكاء والمنطق ---

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_smart_content(self, prompt: str) -> str:
        """توليد محتوى احترافي بلهجة ناصر الخليجية"""
        sys_msg = "أنت ناصر، خبير تقني خليجي. ركز على 'الذكاء الاصطناعي وأحدث أدواته للأفراد'. لا هلوسة، لا رموز صينية، لا إغراق."
        try:
            res = self.gemini.models.generate_content(model="gemini-2.0-flash", contents=f"{sys_msg}\n{prompt}")
            return self._clean_text(res.text)
        except:
            res = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
            )
            return self._clean_text(res.choices[0].message.content)

    def _clean_text(self, text: str) -> str:
        """تنظيف النص من أي شوائب أو هلوسة"""
        text = re.sub(r"[\u4e00-\u9fff]+", "", text) # حذف الصيني
        text = re.sub(r"والله|بالله|إن شاء الله", "", text) # الالتزام بقيود المستخدم
        return text.strip()

    # --- صمام أمان منع الإغراق وقوانين X ---

    def is_safe_to_post(self, current_type: str) -> bool:
        """يتحقق من قوانين منع الإغراق والتكرار"""
        with sqlite3.connect(self.db_path) as conn:
            # 1. منع تكرار نفس النوع مرتين متتاليتين
            last_entry = conn.execute("SELECT content_type, ts FROM history ORDER BY ts DESC LIMIT 1").fetchone()
            if last_entry:
                if last_entry[0] == current_type: return False
                
                # 2. الفاصل الزمني (3 ساعات)
                last_ts = datetime.strptime(last_entry[1], '%Y-%m-%d %H:%M:%S')
                if datetime.now() - last_ts < timedelta(hours=self.MIN_HOURS_BETWEEN_POSTS):
                    logging.info("⏳ لم يمر وقت كافٍ على آخر تغريدة.")
                    return False

            # 3. الحد اليومي (4 تغريدات)
            daily_count = conn.execute("SELECT COUNT(*) FROM history WHERE ts > datetime('now', '-1 day')").fetchone()[0]
            if daily_count >= self.MAX_DAILY_POSTS:
                logging.info("🛑 تم الوصول للحد اليومي للنشر.")
                return False
        return True

    # --- أنواع المحتوى المتنوعة ---

    def post_news_scoop(self):
        """قالب الخبر العاجل"""
        prompt = "اكتب خبر حصري عن أداة AI جديدة للأفراد صدرت في 2026."
        content = self.generate_smart_content(prompt)
        self._publish_to_x(f"🚨 #سبق_تقني\n\n{content}", "NEWS")

    def post_interactive_poll(self):
        """قالب الاستطلاع بالأزرار (تظهر فيه النسب)"""
        # فحص إذا كان هناك استطلاع نشط
        with sqlite3.connect(self.db_path) as conn:
            active_poll = conn.execute("SELECT 1 FROM history WHERE content_type='POLL' AND ts > datetime('now', '-1 day')").fetchone()
            if active_poll: return self.post_news_scoop() # بديل

        question = "بناءً على تجاربكم، أي محرك ذكاء اصطناعي يقدم أدق نتائج باللغة العربية حالياً؟"
        options = ["ChatGPT-5", "Claude 4", "Gemini 2.0 Pro", "Llama 3.3"]
        
        try:
            res = self.x_client.create_tweet(text=f"📊 استطلاع اليوم:\n{question}", poll_options=options, poll_duration_minutes=1440)
            self._save_history(res.data['id'], question, "POLL")
            logging.info("✅ تم نشر استطلاع تفاعلي.")
        except Exception as e: logging.error(f"❌ فشل الاستطلاع: {e}")

    def post_versus_comparison(self):
        """قالب مقارنة العمالقة (Versus)"""
        prompt = "قارن بين أداة Perplexity وأداة SearchGPT من حيث دقة المصادر وسرعة الاستجابة للأفراد."
        content = self.generate_smart_content(prompt)
        self._publish_to_x(f"⚔️ مقارنة العمالقة:\n\n{content}", "VERSUS")

    # --- التنفيذ والحفظ ---

    def _publish_to_x(self, text: str, c_type: str):
        if not self.is_safe_to_post(c_type): return
        try:
            res = self.x_client.create_tweet(text=text[:280])
            self._save_history(res.data['id'], text[:30], c_type)
            logging.info(f"✅ تم نشر محتوى من نوع {c_type}")
        except Exception as e: logging.error(f"❌ فشل النشر: {e}")

    def _save_history(self, tid, topic, c_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (hash, topic, content_type, ts) VALUES (?, ?, ?, datetime('now'))",
                         (str(tid), topic, c_type))

    def run_cycle(self):
        """الد
