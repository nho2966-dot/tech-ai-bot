import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone

import tweepy
from openai import OpenAI

# إعداد المسارات الديناميكية لضمان العمل داخل GitHub Actions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
AUDIT_LOG = os.path.join(BASE_DIR, "audit_log.jsonl")

logging.basicConfig(level=logging.INFO, format="%(message)s")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"

# تم تنظيف هذه القائمة تماماً من أي مسافات مخفية
TECH_TRIGGERS = ["كيف", "لماذا", "ما", "وش", "أفضل", "شرح", "حل", "مشكلة", "خطأ"]

class TechAIExpert:
    def __init__(self):
        logging.info("--- Tech AI Bot [Clean Start] ---")
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.x_client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.content_pillars = {
            "الذكاء الاصطناعي": "Generative AI, AI Agents, ChatGPT",
            "الأمن السيبراني": "Zero Trust, Passkeys, Cybersecurity",
            "البرمجة": "Python, Rust, Clean Code"
        }
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"last_run": None}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def generate_content(self):
        pillar = random.choice(list(self.content_pillars.keys()))
        prompt = f"اكتب ثريد تقني عن {pillar}. افصل بين التغريدات بـ {THREAD_DELIM}. بدون هاشتاقات."
        
        resp = self.ai_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "مختص تقني عربي محترف. أسلوبك: Hook ثم Value ثم CTA."},
                {"role": "user", "content": prompt}
            ]
        )
        content = resp.choices[0].message.content
        tweets = [t.strip() for t in content.split(THREAD_DELIM) if t.strip()]
        tweets[-1] += "\n\n#تقنية #ذكاء_اصطناعي"
        return tweets

    def post_thread(self, tweets):
        prev_id = None
        for tweet in tweets:
            try:
                response = self.x_client.create_tweet(text=tweet, in_reply_to_tweet_id=prev_id, user_auth=True)
                prev_id = response.data['id']
                time.sleep(3)
            except Exception as e:
                logging.error(f"Error: {e}")

    def run(self):
        tweets = self.generate_content()
        self.post_thread(tweets)
        self.state["last_run"] = datetime.now().isoformat()
        self._save_state()

if __name__ == "__main__":
    TechAIExpert().run()
