import os
import time
import random
import hashlib
import sqlite3
import logging
import feedparser
import tweepy
from datetime import datetime
from dotenv import load_dotenv

# استيراد المكتبات الخاصة بالمحركات الثلاثة
from google import genai
from google.genai import types
from openai import OpenAI as OpenAIClient

# 1. إعدادات النظام واللوج
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("SovereignFailover")

# 2. كلاس المحركات الذكية (التسلسل: جمناي -> جوك -> كوين)
class SovereignAI:
    def __init__(self):
        # تحميل المفاتيح من البيئة
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        self.sys_prompt = (
            "أنت خبير تقني سيادي متخصص في Artificial Intelligence and its latest tools والأمن السيبراني. "
            "الهدف: تحليل الأخبار للأفراد وتوعيتهم من الهندسة الاجتماعية. الأسلوب: خليجي، وقور، مهني، ومختصر."
        )

    def generate_content(self, prompt, creative=False):
        # --- المرحلة الأولى: جمناي (Gemini) ---
        try:
            logger.info("Trying Stage 1: Gemini...")
            client = genai.Client(api_key=self.gemini_key)
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.sys_prompt,
                    temperature=0.7 if creative else 0.3
                )
            )
            if resp.text: return resp.text.strip()
        except Exception as e:
            logger.warning(f"⚠️ Gemini failed: {str(e)[:50]}")

        # --- المرحلة الثانية: جوك (Groq) ---
        if self.groq_key:
            try:
                logger.info("Trying Stage 2: Groq (Joke)...")
                client = OpenAIClient(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": self.sys_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7 if creative else 0.3
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"⚠️ Groq failed: {str(e)[:50]}")

        # --- المرحلة الثالثة: كوين (OpenAI) ---
        if self.openai_key:
            try:
                logger.info("Trying Stage 3: OpenAI (Queen)...")
                client = OpenAIClient(api_key=self.openai_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.sys_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"❌ All engines failed: {str(e)[:50]}")
        
        return None

# 3. المنظومة التشغيلية للبوت
class SovereignBot:
    def __init__(self):
        self.ai = SovereignAI()
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    def execute(self):
        # جلب أحدث الأخبار التقنية والأمنية
        feeds = [
            "https://thehackernews.com/feeds/posts/default",
            "https://openai.com/news/rss.xml"
        ]
        pool = []
        for url in feeds:
            f = feedparser.parse(url)
            pool.extend(f.entries[:2])
        
        if not pool: return
        item = random.choice(pool)
        
        # التوليد عبر نظام التسلسل
        content = self.ai.generate_content(f"حلل استراتيجياً للأفراد: {item.title}. المصدر: {item.link}")
        
        if content:
            try:
                # نشر التغريدة مع بصمة غير مرئية لمنع التكرار
                self.x_client.create_tweet(text=f"{content[:270]}\n\u200c🛡️")
                logger.info("✅ Mission Accomplished successfully!")
            except Exception as e:
                logger.error(f"X Post Error: {e}")

if __name__ == "__main__":
    SovereignBot().execute()
