import os
import time
import random
import logging
import feedparser
import tweepy
from google import genai
from google.genai import types
from openai import OpenAI as OpenAIClient

# 1. إعدادات النظام
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("SovereignShield")

class SovereignAI:
    def __init__(self):
        # مطابقة الأسماء مع الصورة التي أرفقتها
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "qwen": os.getenv("QWEN_API_KEY")
        }
        
        self.sys_prompt = (
            "أنت مستشار سيادي في Artificial Intelligence and its latest tools والأمن السيبراني. "
            "حلل الخبر بأسلوب خليجي وقور، مهني، ومختصر جداً للأفراد. حذر من الهندسة الاجتماعية."
        )

    def generate(self, prompt):
        # --- المرحلة 1: جمناي (GEMINI_KEY) ---
        if self.keys["gemini"]:
            try:
                logger.info("🤖 استخدام جمناي...")
                client = genai.Client(api_key=self.keys["gemini"])
                resp = client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=self.sys_prompt)
                )
                if resp.text: return resp.text.strip()
            except Exception as e: logger.warning(f"⚠️ فشل جمناي: {str(e)[:50]}")

        # --- المرحلة 2: جوك (GROQ_API_KEY) ---
        if self.keys["groq"]:
            try:
                logger.info("⚡ استخدام جوك (Groq)...")
                client = OpenAIClient(api_key=self.keys["groq"], base_url="https://api.groq.com/openai/v1")
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": self.sys_prompt}, {"role": "user", "content": prompt}]
                )
                return resp.choices[0].message.content.strip()
            except Exception as e: logger.warning(f"⚠️ فشل جوك: {str(e)[:50]}")

        # --- المرحلة 3: كوين (OPENAI_API_KEY) ---
        if self.keys["openai"]:
            try:
                logger.info("👑 استخدام كوين (OpenAI)...")
                client = OpenAIClient(api_key=self.keys["openai"])
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": self.sys_prompt}, {"role": "user", "content": prompt}]
                )
                return resp.choices[0].message.content.strip()
            except Exception as e: logger.warning(f"⚠️ فشل كوين: {str(e)[:50]}")

        # --- المرحلة 4: Qwen (QWEN_API_KEY) ---
        if self.keys["qwen"]:
            try:
                logger.info("🏮 استخدام Qwen...")
                # تفترض مكتبة OpenAI للتبسيط كون أغلبهم متوافقين
                client = OpenAIClient(api_key=self.keys["qwen"], base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
                resp = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[{"role": "system", "content": self.sys_prompt}, {"role": "user", "content": prompt}]
                )
                return resp.choices[0].message.content.strip()
            except Exception as e: logger.error(f"❌ فشل الكل: {e}")

        return None

class SovereignBot:
    def __init__(self):
        self.ai = SovereignAI()
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def run(self):
        feed = feedparser.parse("https://thehackernews.com/feeds/posts/default")
        if not feed.entries: return
        item = feed.entries[0]
        
        # تنفيذ التحليل بنظام التسلسل
        content = self.ai.generate(f"حلل أمنياً للأفراد: {item.title}. الرابط: {item.link}")
        
        if content:
            try:
                # نشر التغريدة
                self.x.create_tweet(text=f"{content[:275]}\n🛡️")
                logger.info("✅ تم النشر بنجاح سيادي!")
            except Exception as e:
                logger.error(f"X Post Error: {e}")

if __name__ == "__main__":
    SovereignBot().run()
