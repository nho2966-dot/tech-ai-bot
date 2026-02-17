import os
import sqlite3
import logging
import time
import hashlib
import sys
import feedparser
import tweepy
from datetime import datetime, timedelta, timezone
from google import genai
from openai import OpenAI

# إعدادات التسجيل الاحترافية
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignAutonomousSystem:
    def __init__(self):
        # 🔗 الربط مع المسميات الموجودة في إعدادات GitHub الخاصة بك
        self.gemini_key = os.getenv("GEMINI_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")  # مطابق للصورة
        self.groq_key = os.getenv("GROQ_API_KEY")      # مطابق للصورة
        
        # 🧠 إعداد العقول الأربعة
        self._setup_brains()
        
        # 🐦 إعداد منصة X
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True
            )
            logging.info("✅ X Platform: Connected")
        except Exception as e:
            logging.error(f"❌ X Platform Connection Failed: {e}")

        self.db_path = "data/sovereign_v15.db"
        self._init_db()

    def _setup_brains(self):
        # العقل 1 & 4 (Gemini)
        if self.gemini_key:
            self.brain_primary = genai.Client(api_key=self.gemini_key)
            logging.info("✅ Gemini Brain (Impact/Editorial): Ready")
        else:
            logging.error("❌ GEMINI_KEY is missing! Critical Error.")
            sys.exit(1)
        
        # العقل 2 (OpenAI - التحقق)
        if self.openai_key:
            self.brain_verify = OpenAI(api_key=self.openai_key)
            logging.info("✅ OpenAI Brain (Verification): Ready")
        else:
            self.brain_verify = None
            logging.warning("⚠️ OpenAI Key missing, using Gemini as fallback")

        # العقل 3 (Groq - كشف الضجيج)
        if self.groq_key:
            self.brain_hype = OpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
            logging.info("✅ Groq Brain (Hype Detection): Ready")
        else:
            self.brain_hype = None
            logging.warning("⚠️ Groq Key missing, using Gemini as fallback")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, raw_text TEXT, score REAL, ts DATETIME)")

    def is_peak_time(self):
        # ذروة الخليج (8ص - 11م بتوقيت الرياض GMT+3)
        now_riyadh = datetime.now(timezone(timedelta(hours=3)))
        return 8 <= now_riyadh.hour <= 23

    def evaluate_news(self, news_text):
        if not self.is_peak_time(): return
        
        # 1. Impact Score (Gemini)
        res_i = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=f"Rate AI impact (0-10): {news_text}")
        impact = float(''.join(c for c in res_i.text if c.isdigit() or c=='.') or 0)

        # 2. Verify (OpenAI or Gemini fallback)
        if self.brain_verify:
            res_v = self.brain_verify.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"Verify news (0-10): {news_text}"}])
            verify = float(''.join(c for c in res_v.choices[0].message.content if c.isdigit() or c=='.') or 0)
        else: verify = 8.0 

        # 3. Hype Penalty (Groq or Gemini fallback)
        hype = 0.2
        if self.brain_hype:
            res_h = self.brain_hype.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Hype penalty (0-2): {news_text}"}])
            hype = float(''.join(c for c in res_h.choices[0].message.content if c.isdigit() or c=='.') or 0.2)

        final_score = (impact + verify) / 2 - hype
        logging.info(f"📊 Evaluation: Score={final_score:.2f} | Impact={impact} | Verify={verify} | Hype={hype}")

        if final_score >= 9.2 and impact >= 8:
            h = hashlib.md5(news_text.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO waiting_room (hash, raw_text, score, ts) VALUES (?, ?, ?, ?)",
                            (h, news_text, final_score, datetime.now(timezone.utc)))
            logging.info("⏳ الخبر في غرفة الانتظار (تأمل لـ 20 دقيقة)...")

    def process_waiting_room(self):
        with sqlite3.connect(self.db_path) as conn:
            ready = conn.execute("SELECT hash, raw_text FROM waiting_room WHERE ts < ?", 
                                (datetime.now(timezone.utc) - timedelta(minutes=20),)).fetchall()
            for h, text in ready:
                # 4. Editorial Brain (Gemini)
                prompt = f"صغ هذا الخبر بلهجة خليجية مهنية جداً للأفراد، ركز على الفائدة العملية:\n{text}"
                final_post = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
                
                try:
                    self.x_client.create_tweet(text=f"{final_post[:260]}")
                    conn.execute("INSERT INTO memory (hash, ts) VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info("🎯 تم النشر بنجاح!")
                except Exception as e:
                    logging.error(f"❌ النشر فشل: {e}")

if __name__ == "__main__":
    bot = SovereignAutonomousSystem()
    # تجربة فحص أخبار جديدة
    test_news = "OpenAI releases new personal assistant 'Operator' for all users today."
    bot.evaluate_news(test_news)
    # فحص الغرفة للنشر
    bot.process_waiting_room()
