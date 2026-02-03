import os
import sqlite3
import logging
import hashlib
import random
import re
from datetime import datetime, timedelta

import tweepy
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

# 1. الإعدادات العامة
load_dotenv()
DB_FILE = "news.db"

RSS_SOURCES = [
    {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"},
    {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Android Authority", "url": "https://www.androidauthority.com/feed/"}
]

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, replied_at TEXT)")
        # جدول جديد لمتابعة الاستطلاعات ونشر نتائجها
        conn.execute("CREATE TABLE IF NOT EXISTS polls (poll_id TEXT PRIMARY KEY, question TEXT, status TEXT)")
        try:
            conn.execute("SELECT replied_at FROM replies LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE replies ADD COLUMN replied_at TEXT")
        conn.commit()
        conn.close()

    def _init_clients(self):
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api, http_options={'api_version': 'v1'}) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        # نحتاج V1.1 لبعض بيانات الاستطلاع المتقدمة و V2 للنشر
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def ai_ask(self, system_prompt, user_content):
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_prompt}\n\n{user_content}"
            )
            return response.text.strip()
        except Exception:
            try:
                res = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                )
                return res.choices[0].message.content.strip()
            except: return None

    def check_poll_results(self):
        """فحص الاستطلاعات المنتهية ونشر ثريد حول الخيار الفائز"""
        logging.info("📊 فحص نتائج الاستطلاعات...")
        conn = sqlite3.connect(DB_FILE)
        active_polls = conn.execute("SELECT poll_id, question FROM polls WHERE status='active'").fetchall()
        
        for poll_id, question in active_polls:
            try:
                # جلب بيانات الاستطلاع من X
                tweet = self.x_client.get_tweet(poll_id, expansions='attachments.poll_ids').data
                poll_data = self.x_client.get_poll(tweet.attachments['poll_ids'][0]).data
                
                # التحقق إذا انتهى الاستطلاع (X يعيد 'closed')
                if poll_data['voting_status'] == 'closed':
                    options = poll_data['options']
                    winner = max(options, key=lambda x: x['votes'])
                    
                    if winner['votes'] > 0:
                        logging.info(f"🏆 الفائز في الاستطلاع: {winner['label']}")
                        prompt = f"الجمهور اختار '{winner['label']}' في استطلاع رأي حول '{question}'. اكتب ثريد تقني سعودي فخم (4 تغريدات) يحلل هذا الخيار بعمق."
                        content = self.ai_ask("محرر تقني سعودي خبير", prompt)
                        if content and self.post_thread(content):
                            conn.execute("UPDATE polls SET status='completed' WHERE poll_id=?", (poll_id,))
                            conn.commit()
            except Exception as e:
                logging.error(f"❌ Poll Result Error: {e}")
        conn.close()

    def post_thread(self, thread_content):
        """خوارزمية القواعد الذهبية للثريد"""
        clean_content = re.sub(r'^(1/|1\.|1\))\s*', '', thread_content.strip())
        raw_parts = re.split(r'\n\s*\d+[\/\.\)]\s*', clean_content)
        tweets = []
        for part in raw_parts:
            text = part.strip()
            if len(text) > 10:
                if len(text) > 270: text = text[:267].rsplit(' ', 1)[0] + "..."
                tweets.append(text)

        last_tweet_id = None
        for i, tweet in enumerate(tweets[:5]):
            try:
                formatted_tweet = f"{i+1}/ {tweet}"
                if i == 0:
                    response = self.x_client.create_tweet(text=formatted_tweet)
                else:
                    response = self.x_client.create_tweet(text=formatted_tweet, in_reply_to_tweet_id=last_tweet_id)
                last_tweet_id = response.data['id']
            except: break
        return True

    def create_poll(self):
        """إنشاء استطلاع وحفظه في القاعدة لمتابعته"""
        prompt = 'ابتكر استطلاع رأي تقني سعودي فخم (مقارنة بين تقنيتين). النتيجة JSON: {"q": "سؤال", "o": ["1", "2", "3", "4"]}'
        raw = self.ai_ask("خبير استراتيجيات", prompt)
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = eval(match.group())
                res = self.x_client.create_tweet(text=data['q'], poll_options=data['o'], poll_duration_minutes=1440)
                poll_id = res.data['id']
                # حفظ الاستطلاع للمتابعة
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT INTO polls (poll_id, question, status) VALUES (?, ?, ?)", (poll_id, data['q'], 'active'))
                conn.commit()
                conn.close()
                return True
        except: return False

    def run_cycle(self):
        # 1. الرد على المنشن
        self.handle_mentions()
        
        # 2. فحص نتائج الاستطلاعات السابقة (إذا اكتملت ينشر ثريد)
        self.check_poll_results()

        # 3. نشر استطلاع جديد (احتمال 15% لكل دورة لزيادة التفاعل)
        if random.random() < 0.15:
            if self.create_poll(): return

        # 4. النشر العادي من RSS (ثريدات)
        system_instruction = """أنت محرر تقني سعودي خبير. حول الخبر إلى Thread احترافي بالعربي الفخمة (مصطلحات إنجليزية بين قوسين)."""
        random.shuffle(RSS_SOURCES)
        targets = ["apple", "nvidia", "leak", "rumor", "openai", "ai", "تسريب", "iphone", "gpu", "mac", "samsung", "waymo"]

        for src in RSS_SOURCES:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    conn.close()
                    continue

                if any(w in e.title.lower() for w in targets):
                    content = self.ai_ask(system_instruction, f"{e.title}\n{e.description}")
                    if content and any(char in content for char in "أبتثجحخدذرزسشصضطظعغفقكلمنهوي"):
                        if self.post_thread(content):
                            conn.execute("INSERT INTO news (hash, title, published_at) VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                            conn.commit()
                            conn.close()
                            return
                conn.close()

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_cycle()
