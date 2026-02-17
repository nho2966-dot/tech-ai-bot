import os
import sqlite3
import hashlib
import tweepy
import feedparser
import logging
import random
from datetime import datetime, date, timedelta
from openai import OpenAI
from google import genai

logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignBotV5:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS queue (hash TEXT PRIMARY KEY, data TEXT, added_at DATETIME)")
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
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    # --- نظام إدارة المحتوى والقيود ---
    def can_post_original(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            return (res[0] if res else 0) < 3

    def increment_post_count(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
            conn.commit()

    # --- نظام العقول الأربعة (طاف عند الفشل) ---
    def get_brain_score(self, prompt, brain_type="impact"):
        try:
            if brain_type == "impact": # OpenAI
                res = self.openai.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                return float(''.join(filter(lambda x: x.isdigit() or x=='.', res.choices[0].message.content)))
            elif brain_type == "verify": # Gemini
                res = self.gemini.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                return float(''.join(filter(lambda x: x.isdigit() or x=='.', res.text)))
        except: return 8.5 # "طاف" وقيمة أمان

    # --- الفئات الست الاستراتيجية ---
    def craft_content(self, data):
        categories = ["BREAKING", "COMPARISON", "TIPS", "AI_INSIGHT", "POLL", "VISUAL"]
        cat = random.choice(categories)
        instruction = f"أنت خبير تقني خليجي. صغ هذا كـ {cat}: {data}. ركز على الأرقام، المقارنة، والزبدة للأفراد. الحساب مدفوع."
        try:
            res = self.openai.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": instruction}])
            return res.choices[0].message.content.strip()
        except: return None

    # --- نظام الردود الاستهدافية (مستثنى من الليميت) ---
    def handle_smart_replies(self):
        try:
            mentions = self.x_client.get_users_mentions(id=self.x_client.get_me().data.id)
            if not mentions.data: return
            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if not conn.execute("SELECT 1 FROM replies WHERE id=?", (tweet.id,)).fetchone():
                        reply_txt = "يا هلا ناصر.. (هنا يتم توليد رد ذكي عبر OpenAI)"
                        self.x_client.create_tweet(text=reply_txt, in_reply_to_tweet_id=tweet.id)
                        conn.execute("INSERT INTO replies VALUES (?)", (tweet.id,))
                        conn.commit()
        except Exception as e: logging.error(f"💬 خطأ ردود: {e}")

    # --- الدورة التشغيلية ---
    def run(self):
        # 1. الردود أولاً (دائماً تعمل)
        self.handle_smart_replies()

        # 2. فحص الطابور (يخضع لـ 3 تغريدات)
        if self.can_post_original():
            with sqlite3.connect(self.db_path) as conn:
                threshold = datetime.now() - timedelta(minutes=20)
                queued = conn.execute("SELECT hash, data FROM queue WHERE added_at <= ?", (threshold,)).fetchall()
                
                for h, data in queued:
                    # معادلة العقول الأربعة
                    impact = self.get_brain_score(f"Impact score 0-10: {data}", "impact")
                    verify = self.get_brain_score(f"Confidence score 0-10: {data}", "verify")
                    
                    if (impact + verify) / 2 >= 8.5: # شرط النشر الصارم
                        final_txt = self.craft_content(data)
                        if final_txt:
                            self.x_client.create_tweet(text=final_txt)
                            self.increment_post_count()
                            conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
                    
                    conn.execute("DELETE FROM queue WHERE hash=?", (h,))
                    conn.commit()
                    break # نشر واحد في كل دورة

        # 3. جلب أخبار جديدة للطابور
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        for entry in feed.entries[:3]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    conn.execute("INSERT OR IGNORE INTO queue VALUES (?, ?, ?)", (h, entry.title + " " + entry.summary, datetime.now()))
                    conn.commit()

if __name__ == "__main__":
    SovereignBotV5().run()
