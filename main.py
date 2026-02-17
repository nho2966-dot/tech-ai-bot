import os
import sqlite3
import hashlib
import tweepy
import feedparser
import logging
import time
from datetime import datetime, date
from openai import OpenAI
from google import genai

# سجلات التنفيذ
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignBotDirect:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (id TEXT PRIMARY KEY)")

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

    def get_smart_content(self, prompt):
        """العقول المتتابعة: تحاول مع OpenAI، وإذا تعذر فوراً تروح لـ Gemini"""
        try:
            res = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "أنت خبير تقني خليجي متمكن صغ الخبر بلهجة بيضاء قوية ومختصرة جداً."}, 
                          {"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content.strip()
        except:
            try:
                res = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"صغ هذا الخبر بلهجة خليجية تقنية مختصرة: {prompt}"
                )
                return res.text.strip()
            except:
                return None

    def run(self):
        today = date.today().isoformat()
        
        # 1. التحقق من سقف النشر (3 تغريدات)
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            count = res[0] if res else 0
            if count >= 3:
                logging.info(f"✅ تم نشر 3 تغريدات اليوم. نكتفي بهذا القدر.")
                return

        # 2. جلب الأخبار والنشر الفوري
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        
        for entry in feed.entries[:10]: # فحص قائمة أطول لضمان وجود جديد
            h = hashlib.md5(entry.link.encode()).hexdigest()
            
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    # صياغة ونشر
                    logging.info(f"🆕 خبر جديد مكتشف: {entry.title}")
                    final_txt = self.get_smart_content(entry.title)
                    
                    if final_txt:
                        try:
                            # النشر المباشر بدون تعقيدات فلاتر
                            self.x_client.create_tweet(text=final_txt)
                            conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                            conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
                            conn.commit()
                            logging.info("🚀 تم النشر بنجاح.")
                            break # نشر خبر واحد في كل دورة
                        except Exception as e:
                            logging.error(f"❌ خطأ في X API: {e}")
                            break

        # 3. الردود (بشكل مبسط وسريع)
        try:
            mentions = self.x_client.get_users_mentions(id=self.x_client.get_me().data.id, max_results=5)
            if mentions.data:
                for tweet in mentions.data:
                    with sqlite3.connect(self.db_path) as conn:
                        if not conn.execute("SELECT 1 FROM replies WHERE id=?", (tweet.id,)).fetchone():
                            reply_txt = self.get_smart_content(f"رد على هذا الشخص بذكاء: {tweet.text}")
                            if reply_txt:
                                self.x_client.create_tweet(text=reply_txt, in_reply_to_tweet_id=tweet.id)
                                conn.execute("INSERT INTO replies VALUES (?)", (tweet.id,))
                                conn.commit()
                                logging.info(f"💬 تم الرد على {tweet.id}")
        except:
            pass

if __name__ == "__main__":
    SovereignBotDirect().run()
