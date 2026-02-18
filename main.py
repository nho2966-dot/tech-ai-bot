import os
import sqlite3
import hashlib
import logging
import time
import random
import re
from datetime import datetime, timedelta
from collections import deque
import tweepy
from openai import OpenAI
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential
import feedparser
from dateutil import parser as date_parser

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format="🛡️ [إمبراطورية ناصر]: %(message)s")

SYSTEM_PROMPT = r"""
أنت خبير تقني خليجي متخصص في "الذكاء الاصطناعي وأحدث أدواته للأفراد". 
قواعدك الصارمة:
1. ركز على الوكلاء الأذكياء (AI Agents) والأدوات العملية لعام 2026.
2. لا هلوسة، لا كذب، لا افتراضات. إذا لم تجد أداة حقيقية قل "لا_معلومات_موثوقة".
3. ممنوع استخدام كلمة "قسم" أو أي لفظ جلالة.
4. النص باللغة العربية (لهجة خليجية بيضاء) ولا تستخدم أي رموز غريبة أو لغة صينية.
5. الهيكل: فائدة تقنية -> شرح/أداة -> دعوة للتفاعل.
"""

class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()
        self.recent_posts = deque(maxlen=15)

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied_tweets (tweet_id TEXT PRIMARY KEY, ts DATETIME)")

    def _setup_clients(self):
        # إعداد كافة المفاتيح من البيئة (Environment Variables)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        
        # مصفوفة العقول الستة (The 6 Brains)
        self.brains = {
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"),
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "Gemini": self.gemini_client
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_content(self, prompt, sys_msg=SYSTEM_PROMPT, vision_url=None):
        # تتابع العقول لضمان عدم التوقف (Sequence Logic)
        sequence = [
            ("Groq", "llama-3.3-70b-versatile"),
            ("xAI", "grok-2-1212"),
            ("OpenRouter", "deepseek/deepseek-r1"),
            ("Gemini", "gemini-2.0-flash"),
            ("OpenAI", "gpt-4o-mini")
        ]

        for name, model_id in sequence:
            try:
                client = self.brains.get(name)
                if name == "Gemini":
                    content = [sys_msg + "\n" + prompt]
                    if vision_url: content.append(vision_url) # ميزة الرؤية
                    res = client.models.generate_content(model=model_id, contents=content)
                    return self.clean_text(res.text)
                else:
                    res = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                        timeout=20
                    )
                    return self.clean_text(res.choices[0].message.content)
            except Exception as e:
                logging.warning(f"⚠️ {name} فشل، ينتقل للعقل التالي... {str(e)[:50]}")
        return None

    def clean_text(self, text):
        # تنظيف المحتوى من المحظورات والرموز
        forbidden = [r"قسم|والله|بالله|إن شاء الله", r"[\u4e00-\u9fff]+"]
        for p in forbidden: text = re.sub(p, "", text)
        return ' '.join(text.split()).strip()

    def scout_agent(self):
        """الوكيل الصياد: جلب الأخبار وتحويلها لسبق صحفي"""
        feeds = ["https://www.tech-wd.com/wd-rss-feed.xml", "https://feeds.feedburner.com/TheHackersNews"]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                if not self.is_posted(entry.title):
                    scoop = self.generate_content(f"حول هذا الخبر لسبق صحفي عن 'الوكلاء الأذكياء': {entry.title}")
                    if scoop: self.publish(scoop)

    def trend_hijacker(self):
        """خاطف الترندات: استغلال الهاشتاقات النشطة"""
        try:
            # افتراضياً نستخدم وسم نشط في الخليج أو كلمة تقنية رائجة
            trend = "#الذكاء_الاصطناعي" 
            tweet = self.generate_content(f"اكتب تغريدة إبداعية عن 'مستقبل الوكلاء الأذكياء' باستخدام هاشتاق {trend}")
            self.publish(tweet)
        except: pass

    def tech_contest(self):
        """نظام المسابقات: سؤال تفاعلي"""
        question = self.generate_content("صغ سؤال مسابقة ذكي عن أداة AI جديدة مع 3 خيارات.")
        self.publish("🏆 مسابقة ناصر التقنية:\n\n" + question)

    def is_posted(self, text):
        h = hashlib.sha256(text.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone()

    def publish(self, text):
        try:
            h = hashlib.sha256(text.encode()).hexdigest()
            self.x_client.create_tweet(text=text[:280])
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
            logging.info("✅ تم النشر بنجاح!")
        except Exception as e:
            logging.error(f"❌ خطأ نشر: {e}")

    def run(self):
        # ترتيب المهام اليومي
        choice = random.choice(["scout", "trend", "contest"])
        if choice == "scout": self.scout_agent()
        elif choice == "trend": self.trend_hijacker()
        else: self.tech_contest()

if __name__ == "__main__":
    bot = SovereignUltimateBot()
    bot.run()
