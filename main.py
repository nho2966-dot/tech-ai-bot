import os
import sqlite3
import hashlib
import tweepy
import logging
import time
from datetime import datetime, date
from openai import OpenAI
from google import genai

logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class NasserSequentialBrainBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")

    def _setup_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    def get_content_sequential(self, prompt):
        """نظام النقل الآلي: إذا تعطل الأول، الثاني يستلم فوراً"""
        system_msg = (
            "خبير تقني خليجي متمكن. صغ خبر عن Artificial Intelligence and its latest tools "
            "بلهجة خليجية بيضاء، قوية، بدون رموز، بدون صيني، وممنوع الهلوسة."
        )

        # 1. المحاولة بالعقل الأول (OpenAI)
        try:
            logging.info("🧠 جاري محاولة الاستعانة بالعقل الأول (OpenAI)...")
            res = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
                timeout=15 # وقت محدد عشان ما يعلق
            )
            return res.choices[0].message.content.strip()
        
        except Exception as e:
            # إذا جا خطأ 429 أو أي مشكلة، ننتقل فوراً للثاني
            logging.warning(f"⚠️ العقل الأول تعذر (خطأ: {e}). ينتقل للعقل التالي فوراً...")
            
            # 2. المحاولة بالعقل الثاني (Gemini)
            try:
                logging.info("🚀 العقل الثاني (Gemini) يستلم المهمة الآن...")
                res = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{system_msg}\n\nالمهمة: {prompt}"
                )
                return res.text.strip()
            except Exception as ge:
                logging.error(f"❌ حتى العقل الثاني تعثر: {ge}")
                return None

    def run(self):
        today = date.today().isoformat()
        
        # البحث عن خبر جديد (بأمر مباشر للعقول)
        query = "أعطني أحدث أداة ذكاء اصطناعي مفيدة للأفراد ظهرت اليوم مع شرح بسيط لفوائدها."
        final_tweet = self.get_content_sequential(query)
        
        if final_tweet:
            h = hashlib.md5(final_tweet.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    try:
                        # النشر في تويتر
                        self.x_client.create_tweet(text=final_tweet)
                        conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                        conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
                        conn.commit()
                        logging.info("✅ تم النشر بنجاح بفضل نظام العقول المتتابعة.")
                    except Exception as e:
                        logging.error(f"❌ فشل النشر في X: {e}")

if __name__ == "__main__":
    NasserSequentialBrainBot().run()
