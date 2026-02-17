import os
import sqlite3
import logging
import time
import hashlib
import sys
import tweepy
from datetime import datetime, timedelta, timezone
from google import genai
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignBot:
    def __init__(self):
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "xai": os.getenv("XAI_API_KEY")
        }
        self._setup_brains()
        self._setup_x()
        self.db_path = "data/sovereign_v18.db"
        self._init_db()

    def _setup_brains(self):
        self.brain_primary = genai.Client(api_key=self.keys["gemini"]) if self.keys["gemini"] else None
        self.brain_verify = OpenAI(api_key=self.keys["openai"]) if self.keys["openai"] else None
        self.brain_xai = OpenAI(api_key=self.keys["xai"], base_url="https://api.x.ai/v1") if self.keys["xai"] else None

    def _setup_x(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            self.me = self.x_client.get_me().data
            logging.info(f"✅ X Connected: @{self.me.username}")
        except Exception as e:
            logging.error(f"❌ X Connection Failed: {e}")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, score REAL, ts DATETIME)")

    def get_score(self, prompt):
        """نظام المحاولات المتعددة لضمان الحصول على رقم دائماً"""
        # المحاولة 1: Gemini
        if self.brain_primary:
            try:
                time.sleep(1)
                res = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                return float(''.join(c for c in res.text if c.isdigit() or c=='.') or 5.0)
            except: logging.warning("⚠️ Gemini busy...")

        # المحاولة 2: OpenAI
        if self.brain_verify:
            try:
                res = self.brain_verify.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                return float(''.join(c for c in res.choices[0].message.content if c.isdigit() or c=='.') or 5.0)
            except: logging.warning("⚠️ OpenAI busy...")

        # المحاولة 3: xAI
        if self.brain_xai:
            try:
                res = self.brain_xai.chat.completions.create(model="grok-beta", messages=[{"role":"user","content":prompt}])
                return float(''.join(c for c in res.choices[0].message.content if c.isdigit() or c=='.') or 5.0)
            except: pass

        return 5.0 # القيمة المنقذة للحياة (لتجنب الـ None)

    def evaluate_content(self, text):
        impact = self.get_score(f"Rate AI impact 0-10: {text}")
        verify = self.get_score(f"Verify news 0-10: {text}")
        
        # الآن الجمع آمن لأن get_score دائماً ترجع رقم
        final_score = (impact + verify) / 2
        logging.info(f"📊 Final Score: {final_score}")

        if final_score >= 8.0:
            h = hashlib.md5(text.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO waiting_room (hash, content, score, ts) VALUES (?, ?, ?, ?)",
                            (h, text, final_score, datetime.now(timezone.utc)))

    def run_cycle(self):
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            ready = conn.execute("SELECT hash, content FROM waiting_room WHERE ts < ?", (now - timedelta(minutes=20),)).fetchall()
            for h, text in ready:
                try:
                    # الصياغة التحريرية
                    p = f"صغ هذا الخبر بلهجة خليجية مهنية للأفراد: {text}"
                    if self.brain_primary:
                        out = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=p).text
                    else:
                        out = self.brain_xai.chat.completions.create(model="grok-beta", messages=[{"role":"user","content":p}]).choices[0].message.content
                    
                    self.x_client.create_tweet(text=out[:275])
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info("🎯 Tweet Posted!")
                except Exception as e: logging.error(f"❌ Post error: {e}")

if __name__ == "__main__":
    bot = SovereignBot()
    bot.evaluate_content("New AI tool for individual productivity launched by Microsoft.")
    bot.run_cycle()
