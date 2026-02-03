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
        conn.close()

    def _init_clients(self):
        # إعداد Gemini (المحرك الأساسي)
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api, http_options={'api_version': 'v1'}) if g_api else None
        
        # إعداد OpenRouter (المحرك البديل Qwen)
        or_api = os.getenv("OPENROUTER_API_KEY")
        self.ai_qwen = OpenAI(api_key=or_api, base_url="https://openrouter.ai/api/v1") if or_api else None
        
        # إعداد X (مطابقة لمسميات Secrets الخاصة بك)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def ai_ask(self, system_prompt, user_content):
        """توليد محتوى ذكي مع نظام تبديل تلقائي عند الفشل"""
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_prompt}\n\n{user_content}"
            )
            return response.text.strip()
        except Exception as e:
            logging.warning(f"⚠️ Gemini Fallback: {e}")
            try:
                res = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                )
                return res.choices[0].message.content.strip()
            except: return None

    def handle_mentions(self):
        """الرد الذكي على المنشن بأسلوب النخبة"""
        logging.info("🔍 فحص الردود الذكية...")
        try:
            me = self.x_client.get_me().data.id
            mentions = self.x_client.get_users_mentions(id=me, max_results=5).data
            if not mentions: return

            for tweet in mentions:
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone()
                conn.close()

                if not exists:
                    prompt = "أنت خبير تقني سعودي محترف. رد على هذا الاستفسار بأسلوب Elite، مختصر وذكي."
                    reply_text = self.ai_ask(prompt, tweet.text)
                    if reply_text:
                        self.x_client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("INSERT INTO replies VALUES (?, ?)", (str(tweet.id), datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        logging.info(f"✅ تم الرد على: {tweet.id}")
        except Exception as e:
            logging.error(f"❌ Mentions Error: {e}")

    def post_thread(self, thread_content):
        """تحويل النص إلى ثريد مترابط"""
        tweets = [t.strip() for t in re.split(r'\n\d+\. ', thread_content) if t.strip()]
        last_tweet_id = None
        for i, tweet in enumerate(tweets[:4]): # حد أقصى 4 تغريدات للثريد
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
        """إنشاء استطلاع رأي تفاعلي"""
        prompt = 'ابتكر استطلاع رأي تقني فخم. أعطني النتيجة كـ JSON: {"q": "السؤال", "o": ["خيار1", "2", "3", "4"]}'
        raw = self.ai_ask("خبير استراتيجيات", prompt)
        try:
            data = eval(re.search(r'\{.*\}', raw, re.DOTALL).group())
            self.x_client.create_tweet(text=data['q'], poll_options=data['o'], poll_duration_minutes=1440)
            logging.info("📊 تم نشر الاستطلاع.")
            return True
        except: return False

    def run_cycle(self):
        """تشغيل الدورة: ردود -> ثم (نشر خبر/ثريد/أو استطلاع)"""
        self.handle_mentions()

        # اختيار عشوائي لمنع النمط المتكرر (20% استطلاع، 80% أخبار/ثريدات)
        if random.random() < 0.2:
            if self.create_poll(): return

        random.shuffle(RSS_SOURCES)
        targets = ["apple", "nvidia", "leak", "rumor", "openai", "ai", "تسريب", "iphone", "gpu"]

        for src in RSS_SOURCES:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                exists = conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone()
                conn.close()
                if exists: continue

                if any(w in e.title.lower() for w in targets):
                    # طلب ثريد إذا كان المحتوى دسم
                    prompt = "أنت خبير تقني. اكتب ثريد من 3 تغريدات مرقمة عن هذا الخبر بأسلوب فخم جداً."
                    content = self.ai_ask(prompt, f"{e.title}\n{e.description}")
                    if content and self.post_thread(content):
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        logging.info(f"🚀 تم نشر الثريد: {e.title[:30]}")
                        return # منع الإغراق

        # محتوى احتياطي إذا لم يجد شيئاً
        backup = self.ai_ask("خبير تقني", "نصيحة تقنية للنخبة في تغريدة.")
        if backup: self.x_client.create_tweet(text=backup[:280])

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_cycle()
