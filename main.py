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

# إعدادات المراقبة
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignBot:
    def __init__(self):
        # ربط المفاتيح
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "xai": os.getenv("XAI_API_KEY")
        }
        
        self._setup_brains()
        self._setup_x()
        self.db_path = "data/sovereign_v17.db"
        self._init_db()

    def _setup_brains(self):
        self.brain_primary = genai.Client(api_key=self.keys["gemini"]) if self.keys["gemini"] else None
        self.brain_verify = OpenAI(api_key=self.keys["openai"]) if self.keys["openai"] else None
        self.brain_hype = OpenAI(api_key=self.keys["groq"], base_url="https://api.groq.com/openai/v1") if self.keys["groq"] else None
        self.brain_xai = OpenAI(api_key=self.keys["xai"], base_url="https://api.x.ai/v1") if self.keys["xai"] else None

    def _setup_x(self):
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

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, type TEXT, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, score REAL, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS interactions (tweet_id TEXT, user_id TEXT, ts DATETIME)")

    # --- 🧠 منطق "العقل البديل" لتجاوز خطأ الـ 429 ---
    def get_score_with_fallback(self, prompt, brain_type="impact"):
        """يحاول الحصول على النتيجة من عقل، وإذا فشل يحول للآخر"""
        try:
            if brain_type == "impact" and self.brain_primary:
                time.sleep(1) # تأخير بسيط لتجنب الزحام
                res = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                return float(''.join(c for c in res.text if c.isdigit() or c=='.') or 0)
        except Exception as e:
            logging.warning(f"⚠️ Gemini مشغول (429).. أجرب OpenAI")
            
        try:
            if self.brain_verify:
                res = self.brain_verify.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                return float(''.join(c for c in res.choices[0].message.content if c.isdigit() or c=='.') or 0)
        except Exception as e:
            logging.warning(f"⚠️ OpenAI مشغول.. أجرب xAI (Grok)")

        try:
            if self.brain_xai:
                res = self.brain_xai.chat.completions.create(model="grok-beta", messages=[{"role":"user","content":prompt}])
                return float(''.join(c for c in res.choices[0].message.content if c.isdigit() or c=='.') or 0)
        except:
            return 5.0 # قيمة افتراضية في أسوأ الظروف

    def evaluate_content(self, raw_text):
        impact = self.get_score_with_fallback(f"Rate AI impact for individuals 0-10: {raw_text}", "impact")
        verify = self.get_score_with_fallback(f"Is this AI news verifiable 0-10: {raw_text}", "verify")
        
        final_score = (impact + verify) / 2
        logging.info(f"📊 التقييم النهائي: {final_score:.2f}")

        if final_score >= 8.5: # خفضنا النسبة قليلاً لضمان الاستمرارية
            h = hashlib.md5(raw_text.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO waiting_room (hash, content, score, ts) VALUES (?, ?, ?, ?)",
                            (h, raw_text, final_score, datetime.now(timezone.utc)))

    def run_cycle(self):
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            # 1. النشر (مع فحص التوقيت الخليجي)
            ready = conn.execute("SELECT hash, content FROM waiting_room WHERE ts < ?", (now - timedelta(minutes=20),)).fetchall()
            for h, text in ready:
                # صياغة المنشور بالعقل المتاح
                prompt = f"صغ هذا الخبر بلهجة خليجية مهنية للأفراد: {text}"
                try:
                    if self.brain_primary:
                        final_post = self.brain_primary.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
                    else:
                        final_post = self.brain_xai.chat.completions.create(model="grok-beta", messages=[{"role":"user","content":prompt}]).choices[0].message.content
                    
                    self.x_client.create_tweet(text=f"{final_post[:270]}")
                    conn.execute("INSERT INTO history (hash, type, ts) VALUES (?, 'post', ?)", (h, now))
                    conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                    conn.commit()
                    logging.info("🎯 تم النشر بنجاح.")
                except Exception as e: logging.error(f"❌ فشل النشر: {e}")

            # 2. الردود الذكية
            self._handle_mentions()

    def _handle_mentions(self):
        try:
            mentions = self.x_client.get_users_mentions(id=self.me.id)
            if not mentions.data: return
            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT 1 FROM interactions WHERE tweet_id=?", (tweet.id,)).fetchone(): continue
                
                reply_p = f"رد بلهجة خليجية ذكية على: {tweet.text}"
                # استخدام xAI للردود لتقليل الضغط على Gemini
                ans = self.brain_xai.chat.completions.create(model="grok-beta", messages=[{"role":"user","content":reply_p}]).choices[0].message.content
                
                self.x_client.create_tweet(text=f"{ans[:250]}", in_reply_to_tweet_id=tweet.id)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("INSERT INTO interactions (tweet_id, user_id, ts) VALUES (?, ?, ?)", (tweet.id, tweet.author_id, datetime.now(timezone.utc)))
                conn.commit()
        except: pass

if __name__ == "__main__":
    bot = SovereignBot()
    # خبر تجريبي
    bot.evaluate_content("New AI model for coding launched today by a leading startup.")
    bot.run_cycle()
