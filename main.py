import os
import sqlite3
import logging
import time
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from google import genai
from openai import OpenAI
import tweepy

# إعدادات المراقبة
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignAutonomousSystem:
    def __init__(self):
        # 🧠 العقول الأربعة المستقلة
        self.brain_impact = genai.Client(api_key=os.getenv("GEMINI_KEY")) # Gemini
        self.brain_verify = OpenAI(api_key=os.getenv("OPENAI_KEY"))       # OpenAI
        self.brain_hype = OpenAI(api_key=os.getenv("GROQ_KEY"), base_url="https://api.groq.com/openai/v1") # Groq
        self.brain_editorial = self.brain_impact # إعادة استخدام محرك Gemini للصياغة
        
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        self.db_path = "data/sovereign_v14.db"
        self._init_db()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            # الذاكرة التحريرية وغرفة الانتظار
            conn.execute("CREATE TABLE IF NOT EXISTS memory (hash TEXT PRIMARY KEY, type TEXT, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, raw_text TEXT, score REAL, ts DATETIME)")

    # --- بروتوكول الذروة الخليجية ---
    def is_peak_time(self):
        # التركيز على ذروة الاستخدام في الخليج (GMT+3 / GMT+4)
        # من 8 صباحاً إلى 11 مساءً بتوقيت الرياض
        now_riyadh = datetime.now(timezone(timedelta(hours=3)))
        return 8 <= now_riyadh.hour <= 23

    # --- محرك التقييم الرباعي ---
    def evaluate_and_buffer(self, raw_news):
        if not self.is_peak_time():
            logging.info("💤 خارج أوقات الذروة الخليجية.. حفظ المحتوى للدورة القادمة.")
            return

        # 1. Impact Brain (Gemini)
        impact_res = self.brain_impact.models.generate_content(
            model="gemini-2.0-flash", 
            contents=f"Rate AI impact for individuals (0-10): {raw_news}"
        )
        impact_score = float(''.join(filter(lambda x: x.isdigit() or x=='.', impact_res.text)) or 0)

        # 2. Verification Brain (OpenAI)
        verify_res = self.brain_verify.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Is this AI news verifiable? (0-10): {raw_news}"}]
        )
        verify_score = float(''.join(filter(lambda x: x.isdigit() or x=='.', verify_res.choices[0].message.content)) or 0)

        # 3. Hype Brain (Groq/Llama)
        hype_res = self.brain_hype.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Rate market hype/exaggeration (0-2): {raw_news}"}]
        )
        hype_penalty = float(''.join(filter(lambda x: x.isdigit() or x=='.', hype_res.choices[0].message.content)) or 0)

        # المعادلة السيادية
        final_score = (impact_score + verify_score) / 2 - hype_penalty

        if final_score >= 9.2 and impact_score >= 8:
            h = hashlib.md5(raw_news.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO waiting_room (hash, raw_text, score, ts) VALUES (?, ?, ?, ?)",
                            (h, raw_news, final_score, datetime.now(timezone.utc)))
            logging.info(f"✅ تم اجتياز الفحص الأولي (Score: {final_score:.2f}). دخول غرفة الانتظار.")

    # --- محرك النشر بعد "التأمل" ---
    def final_editorial_release(self):
        logging.info("🕒 فحص غرفة الانتظار (إعادة التقييم بعد 20 دقيقة)...")
        with sqlite3.connect(self.db_path) as conn:
            ready_news = conn.execute("SELECT hash, raw_text FROM waiting_room WHERE ts < ?", 
                                     (datetime.now(timezone.utc) - timedelta(minutes=20),)).fetchall()
            
            for h, raw_text in ready_news:
                # العقل الرابع: الصياغة النهائية (Editorial Brain)
                editorial_prompt = f"اكتب تحليلاً سيادياً بلهجة خليجية لهذا الخبر، ركز على 'وش يهم الفرد؟':\n{raw_text}"
                final_post = self.brain_editorial.models.generate_content(
                    model="gemini-2.0-flash", contents=editorial_prompt
                ).text

                try:
                    self.x_client.create_tweet(text=f"{final_post[:250]}\n\n#ذكاء_اصطناعي #تقنية")
                    conn.execute("INSERT INTO memory (hash, ts) VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                    conn.execute("DELETE FROM waiting_room WHERE hash = ?", (h,))
                    conn.commit()
                    logging.info("🎯 تم النشر بنجاح بعد فترة التأمل.")
                except Exception as e:
                    logging.error(f"❌ خطأ نشر: {e}")

if __name__ == "__main__":
    bot = SovereignAutonomousSystem()
    # هنا يتم استلام الخبر من الـ RSS أو البحث
    # bot.evaluate_and_buffer(news_item)
    bot.final_editorial_release()
