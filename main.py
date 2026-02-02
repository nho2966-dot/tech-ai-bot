import os
import sqlite3
import time
import json
import hashlib
import logging
import requests
import random
from datetime import datetime
from urllib.parse import urlparse

import tweepy
import feedparser
from google import genai
from openai import OpenAI
from flask import Flask, render_template
from dotenv import load_dotenv

# ==== إعدادات البيئة والمفاتيح ====
load_dotenv()
DB_FILE = "news.db"

class TechEliteBot:
    def __init__(self):
        self._init_logging()
        self._init_clients()
        self.init_db()
        self._get_my_id()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s")

    def _init_clients(self):
        # عملاء الذكاء الاصطناعي
        self.ai_gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.ai_qwen = OpenAI(api_key=os.getenv("QWEN_API_KEY"), base_url="https://openrouter.ai/api/v1")
        
        # عملاء X (تويتر) - باستخدام المفاتيح التي أرفقتها في كودك
        self.x_client_v2 = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )

    def _get_my_id(self):
        try:
            me = self.x_client_v2.get_me()
            self.my_user_id = me.data.id
        except:
            self.my_user_id = None

    def init_db(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT UNIQUE,
                replied_to INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def safe_ai_request(self, title: str, summary: str, is_reply=False) -> str:
        """نظام توليد المحتوى (جمناي أولاً ثم كوين) مع منع الصينية والهلوسة"""
        instruction = (
            "أنت خبير تقني رصين. صغ تغريدة عربية بناءً على المعلومات التالية فقط.\n"
            "⚠️ قواعد صارمة: لا تستخدم أي رموز صينية، لا تخترع معلومات (لا للهلوسة)، "
            "استخدم العربية مع مصطلحات إنجليزية تقنية بين قوسين."
        )
        if is_reply:
            instruction = "رد على متابع في تويتر بذكاء ودقة تقنية بالعربية فقط، وتجنب الصينية تماماً."

        prompt = f"المحتوى: {title} {summary}"

        # المحاولة 1: جمناي
        try:
            time.sleep(5) # لتجنب ضغط الكوتا
            res = self.ai_gemini.models.generate_content(model="gemini-2.0-flash", contents=f"{instruction}\n\n{prompt}")
            if res.text: return res.text.strip()
        except:
            logging.warning("تنبيه: جمناي ممتلئ، الانتقال إلى كوين (Qwen)...")

        # المحاولة 2: كوين
        try:
            completion = self.ai_qwen.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": instruction}, {"role": "user", "content": prompt}],
                temperature=0.1
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"خطأ في توليد النص: {str(e)}"

    def handle_mentions(self):
        """الرد الذكي على المتابعين"""
        if not self.my_user_id: return
        try:
            mentions = self.x_client_v2.get_users_mentions(id=self.my_user_id, max_results=5)
            if not mentions.data: return
            for tweet in mentions.data:
                # التحقق من قاعدة البيانات لعدم تكرار الرد
                conn = sqlite3.connect(DB_FILE)
                if conn.execute("SELECT id FROM news WHERE link=?", (f"mention_{tweet.id}",)).fetchone():
                    conn.close()
                    continue
                
                reply_text = self.safe_ai_request("رد تفاعلي", tweet.text, is_reply=True)
                self.x_client_v2.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                
                conn.execute("INSERT INTO news (link) VALUES (?)", (f"mention_{tweet.id}",))
                conn.commit()
                conn.close()
        except Exception as e:
            logging.error(f"خطأ في الردود: {e}")

    def process_and_post(self):
        """جلب الأخبار ونشرها (مرة واحدة في كل دورة تشغيل)"""
        RSS_FEEDS = ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"]
        for url in RSS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                conn = sqlite3.connect(DB_FILE)
                if conn.execute("SELECT id FROM news WHERE link=?", (entry.link,)).fetchone():
                    conn.close()
                    continue
                
                # توليد التغريدة
                tweet_text = self.safe_ai_request(entry.title, getattr(entry, "summary", ""))
                
                # النشر
                try:
                    self.x_client_v2.create_tweet(text=tweet_text[:280])
                    conn.execute("INSERT INTO news (link) VALUES (?)", (entry.link,))
                    conn.commit()
                    conn.close()
                    logging.info(f"✅ تم نشر خبر: {entry.title[:30]}")
                    return # نشر خبر واحد فقط لكل تشغيل
                except Exception as e:
                    logging.error(f"فشل النشر: {e}")
                    conn.close()

# ==== Flask Interface ====
app = Flask(__name__)
bot = TechEliteBot()

@app.route("/")
def dashboard():
    return "البوت يعمل بنجاح بنظام (جمناي + كوين) الذكي!"

if __name__ == "__main__":
    # تشغيل المهام
    bot.handle_mentions()   # الرد على المتابعين
    bot.process_and_post()  # نشر خبر جديد
    
    # تشغيل الواجهة (اختياري حسب حاجتك)
    # app.run(host="0.0.0.0", port=5000)
