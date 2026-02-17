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

# إعدادات المراقبة واللوج
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignBot:
    def __init__(self):
        # 🔗 ربط المفاتيح (مطابق لصورتك في GitHub)
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "xai": os.getenv("XAI_API_KEY")
        }
        
        # 🧠 إعداد العقول المتعددة
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
            self.me = self.x_client.get_me().data
            logging.info(f"✅ X Connected: @{self.me.username}")
        except Exception as e:
            logging.error(f"❌ X Connection Failed: {e}")

        self.db_path = "data/sovereign_v16.db"
        self._init_db()

    def _setup_brains(self):
        # العقل الأساسي (Gemini)
        if self.keys["gemini"]:
            self.brain_primary = genai.Client(api_key=self.keys["gemini"])
        else:
            logging.error("❌ Critical: GEMINI_KEY missing!")
            sys.exit(1)

        # عقل التحقق (OpenAI)
        self.brain_verify = OpenAI(api_key=self.keys["openai"]) if self.keys["openai"] else None
        
        # عقل الضجيج (Groq)
        self.brain_hype = OpenAI(api_key=self.keys["groq"], base_url="https://api.groq.com/openai/v1") if self.keys["groq"] else None

        # عقل الطوارئ (xAI)
        self.brain_xai = OpenAI(api_key=self.keys["xai"], base_url="https://api.x.ai/v1") if self.keys["xai"] else None

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, type TEXT, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, score REAL, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS interactions (tweet_id TEXT, user_id TEXT, ts DATETIME)")

    # --- ⚖️ نظام التقييم الرباعي (The Board) ---
    def evaluate_content(self, raw_text):
        # 1. درجة التأثير (Gemini)
        res_i = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=f"Rate AI impact 0-10: {raw_text}")
        impact = float(''.join(c for c in res_i.text if c.isdigit() or c=='.') or 0)

        # 2. درجة الموثوقية (OpenAI)
        verify = 8.0
        if self.brain_verify:
            res_v = self.brain_verify.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"Verify 0-10: {raw_text}"}])
            verify = float(''.join(c for c in res_v.choices[0].message.content if c.isdigit() or c=='.') or 0)

        # 3. عقوبة الضجيج (Groq)
        hype = 0.2
        if self.brain_hype:
            res_h = self.brain_hype.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Hype penalty 0-2: {raw_text}"}])
            hype = float(''.join(c for c in res_h.choices[0].message.content if c.isdigit() or c=='.') or 0.2)

        final_score = (impact + verify) / 2 - hype
        logging.info(f"📊 Score: {final_score:.2f} (I:{impact} V:{verify} H:{hype})")

        if final_score >= 9.2 and impact >= 8:
            h = hashlib.md5(raw_text.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO waiting_room (hash, content, score, ts) VALUES (?, ?, ?, ?)",
                            (h, raw_text, final_score, datetime.now(timezone.utc)))

    # --- 🕒 معالجة غرفة الانتظار والتفاعل ---
    def run_cycle(self):
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            # 1. النشر بعد 20 دقيقة
            ready = conn.execute("SELECT hash, content FROM waiting_room WHERE ts < ?", (now - timedelta(minutes=20),)).fetchall()
            for h, text in ready:
                prompt = f"حلل هذا الخبر بلهجة خليجية مهنية، ركز على 'وش يهمك كفرد؟': {text}"
                final_post = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
                
                try:
                    self.x_client.create_tweet(text=final_post[:270])
                    conn.execute("INSERT INTO history (hash, type, ts) VALUES (?, 'post', ?)", (h, now))
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info("🎯 Published successfully.")
                except Exception as e: logging.error(f"❌ Post failed: {e}")

            # 2. التفاعل مع الردود (Smart Interaction)
            self._handle_mentions()

    def _handle_mentions(self):
        logging.info("💬 Checking mentions...")
        try:
            mentions = self.x_client.get_users_mentions(id=self.me.id)
            if not mentions.data: return
            
            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT 1 FROM interactions WHERE tweet_id=?", (tweet.id,)).fetchone(): continue
                
                reply_prompt = f"رد بلهجة خليجية ذكية ومختصرة على: {tweet.text}"
                ans = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=reply_prompt).text
                
                self.x_client.create_tweet(text=f"{ans[:250]}", in_reply_to_tweet_id=tweet.id)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("INSERT INTO interactions (tweet_id, user_id, ts) VALUES (?, ?, ?)", 
                                (tweet.id, tweet.author_id, datetime.now(timezone.utc)))
                conn.commit()
        except Exception as e: logging.error(f"💬 Interaction error: {e}")

if __name__ == "__main__":
    bot = SovereignBot()
    # إضافة خبر تجريبي (يمكنك استبداله بـ RSS Scraper لاحقاً)
    bot.evaluate_content("OpenAI launches search engine SearchGPT for all pro users.")
    bot.run_cycle()
