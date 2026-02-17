import os
import sqlite3
import hashlib
import tweepy
import logging
import time
from datetime import datetime, date
from openai import OpenAI
from google import genai

# إعداد السجلات - نظام الرقابة الصارم
logging.basicConfig(level=logging.INFO, format="🛡️ [نظام السيادة]: %(message)s")

class SovereignSixBrainsBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_brains()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")

    def _setup_brains(self):
        # تجهيز العقول للعمل المتتابع
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        except Exception as e:
            logging.error(f"❌ عطل في ربط العقول: {e}")

    def execute_sequential_brain(self, task_prompt):
        """نظام العقول الستة المتتابعة - الانتقال الفوري عند أي تعثر"""
        
        # مسميات العقول حسب الترتيب القتالي
        brains_models = [
            ("العقل الأول (GPT-4o)", "openai", "gpt-4o"),
            ("العقل الثاني (Gemini 2.0 Flash)", "gemini", "gemini-2.0-flash"),
            ("العقل الثالث (GPT-4-Turbo)", "openai", "gpt-4-turbo"),
            ("العقل الرابع (Gemini 1.5 Pro)", "gemini", "gemini-1.5-pro"),
            ("العقل الخامس (GPT-3.5-Turbo)", "openai", "gpt-3.5-turbo"),
            ("العقل السادس (Gemini 1.5 Flash)", "gemini", "gemini-1.5-flash")
        ]

        system_instructions = (
            "أنت خبير تقني خليجي متمكن في Artificial Intelligence and its latest tools. "
            "صغ المحتوى بلهجة خليجية بيضاء، قوية، ومختصرة جداً للأفراد. "
            "ممنوع الهلوسة، ممنوع الرموز، ممنوع الصيني. ركز على الفائدة الحقيقية."
        )

        for name, provider, model_id in brains_models:
            try:
                logging.info(f"🧠 جاري محاولة التنفيذ عبر: {name}...")
                
                if provider == "openai":
                    res = self.openai_client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": system_instructions}, {"role": "user", "content": task_prompt}],
                        timeout=10
                    )
                    return res.choices[0].message.content.strip()
                
                elif provider == "gemini":
                    res = self.gemini_client.models.generate_content(
                        model=model_id,
                        contents=f"{system_instructions}\n\nالمهمة: {task_prompt}"
                    )
                    return res.text.strip()

            except Exception as e:
                logging.warning(f"⚠️ {name} واجه مشكلة (429 أو Quota). ينتقل للعقل التالي فوراً...")
                continue # الانتقال للعقل اللي بعده

        logging.error("❌ تم استنفاد جميع العقول الستة دون جدوى.")
        return None

    def run(self):
        today = date.today().isoformat()
        
        # فحص السقف اليومي لضمان السيادة وعدم الحظر
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            if res and res[0] >= 5:
                logging.info("🛡️ تم تحقيق هدف النشر اليومي.")
                return

        # المهمة: البحث عن أدوات ذكاء اصطناعي حديثة للأفراد
        task = "ابحث عن أحدث أداة Artificial Intelligence and its latest tools مفيدة للأفراد اليوم وصغها في تغريدة خليجية."
        
        content = self.execute_sequential_brain(task)
        
        if content:
            h = hashlib.md5(content.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    try:
                        self.x_client.create_tweet(text=content)
                        conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                        conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
                        conn.commit()
                        logging.info("🚀 تم النشر بنجاح بفضل تسلسل العقول الستة.")
                    except Exception as e:
                        logging.error(f"❌ خطأ في منصة X: {e}")

if __name__ == "__main__":
    SovereignSixBrainsBot().run()
