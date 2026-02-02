import os
import time
import json
import hashlib
import logging
import requests
import random
from typing import Optional
from urllib.parse import urlparse

import tweepy
import feedparser
from google import genai
from openai import OpenAI

SOURCES = [
    "https://ai.googleblog.com/atom.xml",
    "https://www.microsoft.com/en-us/research/feed/",
    "https://engineering.fb.com/feed/",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://arstechnica.com/feed/",
    "https://www.wired.com/feed/rss"
]

STATE_FILE = "state.json"
MAX_POSTS = 2 

class TechEliteHybridBot:
    def __init__(self):
        self._init_logging()
        self._load_env()
        self._init_clients()
        self.state = self._load_state()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s")

    def _load_env(self):
        self.GEMINI_KEY = os.getenv("GEMINI_KEY")
        self.QWEN_KEY = os.getenv("QWEN_API_KEY")
        self.X_API_KEY = os.getenv("X_API_KEY")
        self.X_API_SECRET = os.getenv("X_API_SECRET")
        self.X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
        self.X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
        self.X_BEARER = os.getenv("X_BEARER_TOKEN")

    def _init_clients(self):
        self.ai_gemini = genai.Client(api_key=self.GEMINI_KEY)
        self.ai_qwen = OpenAI(
            api_key=self.QWEN_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        auth = tweepy.OAuth1UserHandler(self.X_API_KEY, self.X_API_SECRET, self.X_ACCESS_TOKEN, self.X_ACCESS_SECRET)
        self.x_api_v1 = tweepy.API(auth)
        self.x_client_v2 = tweepy.Client(
            bearer_token=self.X_BEARER,
            consumer_key=self.X_API_KEY,
            consumer_secret=self.X_API_SECRET,
            access_token=self.X_ACCESS_TOKEN,
            access_token_secret=self.X_ACCESS_SECRET
        )

    def _load_state(self):
        if not os.path.exists(STATE_FILE): return {"hashes": []}
        try:
            with open(STATE_FILE, "r") as f: return json.load(f)
        except: return {"hashes": []}

    def _save_state(self):
        with open(STATE_FILE, "w") as f: json.dump(self.state, f)

    def safe_ai_request(self, title: str, summary: str, source: str) -> Optional[str]:
        # تعليمات صارمة جداً لمنع الهلوسة والمصطلحات الصينية
        instruction = (
            "أنت خبير تقني عالمي. صغ تغريدة عربية بناءً على المعلومات المرفقة فقط.\n"
            "⚠️ قواعد صارمة:\n"
            "1. ممنوع نهائياً استخدام أي مصطلحات أو رموز صينية.\n"
            "2. الالتزام باللغة العربية مع المصطلحات التقنية الإنجليزية فقط.\n"
            "3. ممنوع اختراع معلومات غير موجودة (لا للهلوسة).\n"
            "4. الأسلوب: Hook جذاب + معلومة تقنية + نصيحة (Pro Tip)."
        )
        user_content = f"الخبر: {title}\nالتفاصيل: {summary}\nالمصدر: {source}"

        # 1. الخيار الأول: جمناي
        try:
            logging.info("🚀 Gemini Primary Attempt...")
            time.sleep(10)
            res = self.ai_gemini.models.generate_content(
                model="gemini-2.0-flash", 
                contents=f"{instruction}\n\n{user_content}"
            )
            if res.text: return res.text.strip()
        except Exception as e:
            logging.warning(f"⚠️ Gemini Busy. Switching to Qwen...")

        # 2. الخيار الثاني: كوين (مع إعدادات الدقة القصوى)
        try:
            if not self.QWEN_KEY: return None
            logging.info("🔄 Qwen Fallback (Strict No-Chinese Mode)...")
            completion = self.ai_qwen.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1, # لضمان الواقعية وعدم التخريف
                max_tokens=300
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"❌ All Models Failed: {e}")
            return None

    def run(self):
        logging.info("Cycle Started - Secure Hybrid Mode")
        posted = 0
        for src in random.sample(SOURCES, len(SOURCES)):
            if posted >= MAX_POSTS: break
            feed = feedparser.parse(src)
            for entry in feed.entries[:5]:
                h = hashlib.md5(entry.title.encode()).hexdigest()
                if h in self.state["hashes"] or posted >= MAX_POSTS: continue

                tweet = self.safe_ai_request(entry.title, getattr(entry, "summary", ""), urlparse(entry.link).netloc)
                if tweet:
                    try:
                        self.x_client_v2.create_tweet(text=tweet[:280])
                        self.state["hashes"].append(h)
                        self._save_state()
                        posted += 1
                        logging.info(f"✅ Success: {entry.title[:30]}")
                        time.sleep(60)
                    except Exception as e: logging.error(f"X Error: {e}")

if __name__ == "__main__":
    TechEliteHybridBot().run()
