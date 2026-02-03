import os
import sqlite3
import logging
import hashlib
import random
import re
from datetime import datetime

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
        conn.commit()
        conn.close()

    def _init_clients(self):
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api, http_options={'api_version': 'v1'}) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False
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

    def handle_mentions(self):
        logging.info("🔍 فحص الردود الذكية...")
        try:
            me = self.x_client.get_me().data.id
            mentions = self.x_client.get_users_mentions(id=me, max_results=5).data
            if not mentions: return
            for tweet in mentions:
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone()
                if not exists:
                    reply_text = self.ai_ask("أنت خبير تقني سعودي فخم. رد بذكاء واختصار.", tweet.text)
                    if reply_text:
                        self.x_client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                        conn.execute("INSERT INTO replies (tweet_id, replied_at) VALUES (?, ?)", (str(tweet.id), datetime.now().isoformat()))
                        conn.commit()
                        logging.info(f"✅ تم الرد على: {tweet.id}")
                conn.close()
        except tweepy.TooManyRequests:
            logging.warning("⚠️ حد طلبات X، تخطي الردود.")
        except Exception as e:
            logging.error(f"❌ Mentions Error: {e}")

    def post_thread(self, thread_content):
        """خوارزمية تقسيم ونشر الثريد الاحترافي (القواعد الذهبية)"""
        # تقسيم مرن يتعرف على 1/ أو 1. أو 1)
        tweets = re.split(r'\n\d+[\/\.\)]\s*', thread_content)
        tweets = [t.strip() for t in tweets if len(t.strip()) > 10]

        last_tweet_id = None
        for i, tweet in enumerate(tweets[:5]):
            try:
                formatted_tweet = f"{i+1}/ {tweet}"
                # صمام أمان الحجم
                if len(formatted_tweet) > 280:
                    formatted_tweet = formatted_tweet[:277] + "..."

                if i == 0:
                    response = self.x_client.create_tweet(text=formatted_tweet)
                else:
                    response = self.x_client.create_tweet(text=formatted_tweet, in_reply_to_tweet_id=last_tweet_id)
                
                last_tweet_id = response.data['id']
                logging.info(f"🧵 تم نشر الجزء {i+1}")
            except Exception as e:
                logging.error(f"❌ خطأ جزء الثريد: {e}")
                break
        return True

    def create_poll(self):
        prompt = 'ابتكر استطلاع رأي تقني. النتيجة JSON حصراً: {"q": "سؤال", "o": ["1", "2", "3", "4"]}'
        raw = self.ai_ask("خبير استراتيجيات", prompt)
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = eval(match.group())
                self.x_client.create_tweet(text=data['q'], poll_options=data['o'], poll_duration_minutes=1440)
                return True
        except: return False

    def run_cycle(self):
        self.handle_mentions()
        if random.random() < 0.2:
            if self.create_poll(): return

        # القواعد الذهبية للصياغة داخل البرومبت
        system_instruction = """أنت محرر تقني خبير (Elite Tech Editor). حول الخبر إلى Thread احترافي وفق القواعد:
        1. التغريدة الأولى: Hook جذاب بدون تفاصيل معقدة.
        2. التقسيم: 3-4 تغريدات مرقمة (1/، 2/...).
        3. المصطلحات: إنجليزي بجانب العربي، مثال: AI (الذكاء الاصطناعي).
        4. الإيموجي: بحكمة لتعزيز المعنى.
        5. الاستقلالية: كل تغريدة مفهومة بذاتها."""

        random.shuffle(RSS_SOURCES)
        targets = ["apple", "nvidia", "leak", "rumor", "openai", "ai", "تسريب", "iphone", "gpu", "mac"]

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
                    if content and self.post_thread(content):
                        conn.execute("INSERT INTO news (hash, title, published_at) VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        logging.info(f"🚀 تم نشر الثريد الاحترافي.")
                        return
                conn.close()

        backup = self.ai_ask("خبير تقني", "نصيحة تقنية ذكية جداً في تغريدة.")
        if backup: self.x_client.create_tweet(text=backup[:280])

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_cycle()
