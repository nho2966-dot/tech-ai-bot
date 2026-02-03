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
        """إنشاء الجداول وضمان ثبات الهيكل"""
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, replied_at TEXT)")
        conn.commit()
        conn.close()

    def _init_clients(self):
        # Gemini (المحرك الأساسي)
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api, http_options={'api_version': 'v1'}) if g_api else None
        
        # OpenRouter (المحرك البديل)
        or_api = os.getenv("OPENROUTER_API_KEY")
        self.ai_qwen = OpenAI(api_key=or_api, base_url="https://openrouter.ai/api/v1") if or_api else None
        
        # X Client (V2)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def ai_ask(self, system_prompt, user_content):
        """محاولة Gemini ثم البديل Qwen"""
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
        """الرد الذكي مع ضمان عدم تكرار الرد"""
        logging.info("🔍 فحص الردود الذكية...")
        try:
            me = self.x_client.get_me().data.id
            mentions = self.x_client.get_users_mentions(id=me, max_results=5).data
            if not mentions: return

            for tweet in mentions:
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone()
                
                if not exists:
                    prompt = "أنت خبير تقني سعودي فخم. رد على هذا الاستفسار بأسلوب ذكي ومختصر."
                    reply_text = self.ai_ask("خبير تقني", tweet.text)
                    if reply_text:
                        self.x_client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                        conn.execute("INSERT INTO replies (tweet_id, replied_at) VALUES (?, ?)", (str(tweet.id), datetime.now().isoformat()))
                        conn.commit()
                        logging.info(f"✅ تم الرد على: {tweet.id}")
                conn.close()
        except Exception as e:
            logging.error(f"❌ Mentions Error: {e}")

    def post_thread(self, thread_content):
        """تحويل النص المولد إلى ثريد مترابط"""
        tweets = [t.strip() for t in re.split(r'\n\d+\. ', thread_content) if t.strip()]
        last_tweet_id = None
        for i, tweet in enumerate(tweets[:4]):
            try:
                text = f"{i+1}/ {tweet}"
                if i == 0:
                    response = self.x_client.create_tweet(text=text[:280])
                else:
                    response = self.x_client.create_tweet(text=text[:280], in_reply_to_tweet_id=last_tweet_id)
                last_tweet_id = response.data['id']
            except: break
        return True

    def create_poll(self):
        """إنشاء استطلاع رأي تقني"""
        prompt = 'ابتكر استطلاع رأي تقني. النتيجة كـ JSON حصراً: {"q": "سؤال", "o": ["1", "2", "3", "4"]}'
        raw = self.ai_ask("خبير استراتيجيات", prompt)
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = eval(match.group())
                self.x_client.create_tweet(text=data['q'], poll_options=data['o'], poll_duration_minutes=1440)
                logging.info("📊 تم نشر الاستطلاع.")
                return True
        except: return False

    def run_cycle(self):
        """تشغيل الدورة الكاملة مع منع الإغراق"""
        self.handle_mentions()

        # احتمال 20% للاستطلاعات لكسر الروتين
        if random.random() < 0.2:
            if self.create_poll(): return

        random.shuffle(RSS_SOURCES)
        targets = ["apple", "nvidia", "leak", "rumor", "openai", "ai", "تسريب", "iphone", "gpu", "mac"]

        for src in RSS_SOURCES:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone()
                
                if exists:
                    conn.close()
                    continue

                if any(w in e.title.lower() for w in targets):
                    prompt = "أنت خبير تقني سعودي فخم. اكتب ثريد من 3 تغريدات مرقمة عن هذا الخبر."
                    content = self.ai_ask(prompt, f"{e.title}\n{e.description}")
                    if content and self.post_thread(content):
                        # الإدخال الصريح لمنع أخطاء عدد الأعمدة
                        conn.execute("INSERT INTO news (hash, title, published_at) VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        logging.info(f"🚀 تم نشر الخبر بنجاح.")
                        return
                conn.close()

        # خطة الطوارئ: نصيحة تقنية
        backup = self.ai_ask("خبير تقني", "قدم نصيحة تقنية ذكية جداً في تغريدة واحدة.")
        if backup: self.x_client.create_tweet(text=backup[:280])

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_cycle()
