import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone

import tweepy
from openai import OpenAI
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# إعداد المسارات لضمان العمل داخل GitHub Actions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
AUDIT_LOG = os.path.join(BASE_DIR, "audit_log.jsonl")

logging.basicConfig(level=logging.INFO, format="%(message)s")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"

class TechAIExpert:
    def __init__(self):
        logging.info("--- Tech AI Bot [Production Version] ---")
        self._init_clients()
        self.content_pillars = {
            "الذكاء الاصطناعي": "أحدث نماذج LLM وتطبيقات AI Agents.",
            "البرمجة": "تطوير البرمجيات باستخدام Python و Rust.",
            "الأمن السيبراني": "حماية البيانات وتقنيات التشفير الحديثة."
        }
        self.state = self._load_state()

    def _init_clients(self):
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

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"last_run": None, "posted_count": 0}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def fix_arabic(self, text):
        """تجهيز النص العربي للعرض الصحيح في الصور أو الأنظمة التي لا تدعمه"""
        reshaped_text = reshape(text)
        return get_display(reshaped_text)

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
        # إضافة الهاشتاقات لآخر تغريدة فقط
        tweets[-1] += "\n\n#تقنية #ذكاء_اصطناعي"
        return tweets

    def post_thread(self, tweets):
        prev_id = None
        for tweet in tweets:
            try:
                response = self.x_client.create_tweet(text=tweet, in_reply_to_tweet_id=prev_id, user_auth=True)
                prev_id = response.data['id']
                logging.info(f"✅ Posted: {prev_id}")
                time.sleep(5) # فاصل زمني لتجنب الـ Spam
            except Exception as e:
                logging.error(f"❌ Error posting: {e}")

    def run(self):
        tweets = self.generate_content()
        self.post_thread(tweets)
        self.state["last_run"] = datetime.now().isoformat()
        self.state["posted_count"] += 1
        self._save_state()

if __name__ == "__main__":
    TechAIExpert().run()
