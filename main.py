import os
import sqlite3
import hashlib
import logging
import time
import random
import re
from datetime import datetime, timedelta
from collections import deque
from typing import List, Dict, Any

import tweepy
from openai import OpenAI
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential
import feedparser
from dateutil import parser as date_parser

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format="🛡️ [إمبراطورية ناصر]: %(message)s")

SYSTEM_PROMPT = r"""
أنت خبير تقني خليجي رائد (ناصر). تخصصك: "الذكاء الاصطناعي وأحدث أدواته للأفراد" و"الوكلاء الأذكياء".
- اللهجة: خليجية بيضاء، احترافية، مختصرة.
- الموثوقية: 100%، لا هلوسة، لا كذب. إذا لم تجد أداة حقيقية قل "لا_معلومات_موثوقة".
- القيود: ممنوع القسم، لفظ الجلالة، اللغة الصينية، أو الرموز الغريبة.
- الهدف: فائدة عملية للفرد + أداة حقيقية + وسائط بصرية.
"""

class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_2026.db"
        self._init_db()
        self._setup_clients()
        self.rss_feeds = [
            "https://www.tech-wd.com/wd-rss-feed.xml",
            "https://www.aitnews.com/feed/",
            "https://openai.com/blog/rss/"
        ]

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, topic TEXT, content_type TEXT, ts DATETIME, analyzed INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied_tweets (tweet_id TEXT PRIMARY KEY, ts DATETIME)")

    def _setup_clients(self):
        # إعداد مفاتيح API من البيئة (GitHub Secrets)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.brains = {
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "Gemini": self.gemini_client
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_content(self, prompt: str, sys_msg: str = SYSTEM_PROMPT) -> str:
        try:
            # استخدام Gemini 2.0 كعقل أساسي للرؤية والمنطق
            res = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=f"{sys_msg}\n{prompt}"
            )
            return self.clean_text(res.text)
        except Exception:
            # العقل الاحتياطي (Llama 3.3)
            client = self.brains["Groq"]
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
            )
            return self.clean_text(res.choices[0].message.content)

    def clean_text(self, text: str) -> str:
        text = re.sub(r"قسم|والله|بالله|إن شاء الله", "", text)
        text = re.sub(r"[\u4e00-\u9fff]+", "", text) # حذف الصيني
        return ' '.join(text.split()).strip()

    def get_diverse_template(self) -> Dict:
        templates = [
            {"type": "NEWS", "p": "صغ سبق تقني عن أداة AI جديدة.", "s": "🚨 #سبق_تقني"},
            {"type": "TIP", "p": "أعط نصيحة عملية للفرد باستخدام الوكلاء الأذكياء.", "s": "🛠️ نصيحة ناصر"},
            {"type": "POLL", "p": "صغ استطلاع رأي عن صراع أدوات AI مع خيارات.", "s": "📊 تصويت"},
            {"type": "DEEP", "p": "شرح عميق لتقنية Agentic AI.", "s": "💡 معلومة عميقة"}
        ]
        return random.choice(templates)

    def publish_with_media(self, text: str, topic: str, c_type: str):
        """توليد ميديا (صورة/فيديو) ونشرها مع التغريدة"""
        h = hashlib.sha256(text.encode()).hexdigest()
        if self.is_already_posted(h): return

        try:
            # هنا يتم استدعاء أدوات التوليد (المحاكاة للـ API)
            # visual_prompt = f"Futuristic high-tech visual for {topic}"
            # media_id = self.x_client.media_upload(filename="generated_ai_video.mp4")
            
            self.x_client.create_tweet(text=text[:280])
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO history (hash, topic, content_type, ts) VALUES (?, ?, ?, datetime('now'))", 
                             (h, topic, c_type))
            logging.info(f"✅ تم نشر {c_type}")
        except Exception as e:
            logging.error(f"❌ خطأ نشر: {e}")

    def is_already_posted(self, h: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            return bool(conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone())

    def run_strategic_mission(self):
        # 1. اختيار قالب عشوائي
        tmpl = self.get_diverse_template()
        
        # 2. توليد المحتوى
        content = self.generate_content(tmpl["p"])
        final_text = f"{tmpl['s']}\n\n{content}"
        
        # 3. النشر
        self.publish_with_media(final_text, content[:30], tmpl["type"])

if __name__ == "__main__":
    bot = SovereignUltimateBot()
    bot.run_strategic_mission()
