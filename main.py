import os, sqlite3, logging, hashlib, time, random, textwrap
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- الإعدادات السيادية ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class TechSovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS content_memory 
                         (h TEXT PRIMARY KEY, h_link TEXT, type TEXT, topic TEXT, dt TEXT)""")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, text_hash TEXT, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        # محاولة تعريف العميل مع معالجة الأخطاء
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True # تفعيل الانتظار التلقائي عند الوصول للحد
            )
            self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        except Exception as e:
            logging.error(f"Client Init Error: {e}")

    def _safe_ai_call(self, sys_p, user_p):
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
                temperature=0.15
            )
            return r.choices[0].message.content.strip()
        except: return None

    def run(self):
        # تقليل عدد المحاولات لتجنب الـ Rate Limit
        task_type = random.choice(["ai_tool", "productivity"])
        content = self._safe_ai_call("خبير تقني.", f"اكتب تغريدة عن {task_type} للثورة الرابعة.")
        
        if content:
            try:
                # محاولة النشر
                self.x.create_tweet(text=content[:280])
                logging.info("✅ Tweet posted successfully!")
            except tweepy.errors.TooManyRequests:
                logging.warning("⚠️ X Rate limit reached. Sleeping for now...")
            except Exception as e:
                logging.error(f"Posting Error: {e}")

if __name__ == "__main__":
    TechSovereignEngine().run()
