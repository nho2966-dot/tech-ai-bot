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

class TechEliteFinalBot:
    def __init__(self):
        self._init_logging()
        self._load_env()
        self._init_clients()
        self.state = self._load_state()
        try:
            # محاولة جلب ID الحساب للردود
            me = self.x_client_v2.get_me()
            self.my_user_id = me.data.id
        except Exception as e:
            logging.error(f"Could not get User ID: {e}")
            self.my_user_id = None

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
        self.ai_qwen = OpenAI(api_key=self.QWEN_KEY, base_url="https://openrouter.ai/api/v1")
        
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
        if not os.path.exists(STATE_FILE): return {"hashes": [], "replied_ids": []}
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                if "replied_ids" not in data: data["replied_ids"] = []
                return data
        except: return {"hashes": [], "replied_ids": []}

    def _save_state(self):
        with open(STATE_FILE, "w") as f: json.dump(self.state, f)

    def safe_ai_request(self, title: str, summary: str, source: str, is_reply=False) -> Optional[str]:
        instruction = (
            "أنت خبير تقني عالمي. صغ تغريدة عربية بناءً على المعلومات المرفقة فقط.\n"
            "⚠️ قواعد صارمة جداً:\n"
            "1. يمنع منعاً باتاً استخدام أي حرف أو رمز أو مصطلح صيني.\n"
            "2. الالتزام بالعربية الرصينة والمصطلحات الإنجليزية (بين قوسين).\n"
            "3. لا تخترع ميزات غير موجودة في النص (منع الهلوسة).\n"
            "4. الأسلوب بشري، تفاعلي، مشوق."
        )
        if is_reply:
            instruction = "أنت مساعد ذكي على X. رد على المتابع بذكاء ودقة تقنية بالعربية فقط، دون أي صينية."

        user_content = f"الموضوع: {title}\nالتفاصيل: {summary}\nالمصدر: {source}"

        # 1. جمناي (الخيار الأول)
        try:
            time.sleep(10)
            res = self.ai_gemini.models.generate_content(model="gemini-2.0-flash", contents=f"{instruction}\n\n{user_content}")
            if res.text: return res.text.strip()
        except:
            logging.warning("Switching to Qwen due to Gemini limit...")

        # 2. كوين (الاحتياطي)
        try:
            if not self.QWEN_KEY: return None
            completion = self.ai_qwen.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": instruction}, {"role": "user", "content": user_content}],
                temperature=0.1
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Failure: {e}")
            return None

    def handle_mentions(self):
        if not self.my_user_id: return
        logging.info("🔍 Scanning Mentions...")
        try:
            mentions = self.x_client_v2.get_users_mentions(id=self.my_user_id, max_results=10)
            if not mentions.data: return

            for tweet in mentions.data:
                if tweet.id in self.state["replied_ids"]: continue
                
                reply = self.safe_ai_request("Interaction", tweet.text, "User Mention", is_reply=True)
                if reply:
                    self.x_client_v2.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    self.state["replied_ids"].append(tweet.id)
                    self._save_state()
                    logging.info(f"✅ Replied to: {tweet.id}")
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def run(self):
        self.handle_mentions()
        
        posted = 0
        for src in random.sample(SOURCES, len(SOURCES)):
            if posted >= 1: break
            feed = feedparser.parse(src)
            for entry in feed.entries[:5]:
                h = hashlib.md5(entry.title.encode()).hexdigest()
                if h in self.state["hashes"]: continue

                tweet = self.safe_ai_request(entry.title, getattr(entry, "summary", ""), urlparse(entry.link).netloc)
                if tweet:
                    try:
                        self.x_client_v2.create_tweet(text=tweet[:280])
                        self.state["hashes"].append(h)
                        self._save_state()
                        posted += 1
                        logging.info(f"✅ Published: {entry.title[:30]}")
                        break
                    except Exception as e:
                        logging.error(f"X Post Error: {e}")
                        continue

if __name__ == "__main__":
    TechEliteFinalBot().run()
