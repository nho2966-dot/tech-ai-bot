import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone

import tweepy
from openai import OpenAI

# إعداد المسارات - لضمان العمل داخل GitHub Actions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
AUDIT_LOG = os.path.join(BASE_DIR, "audit_log.jsonl")

logging.basicConfig(level=logging.INFO, format="%(message)s")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)

# قائمة الكلمات المفتاحية منظفة تماماً من أي رموز مخفية
TECH_TRIGGERS = ["كيف", "لماذا", "ما", "وش", "أفضل", "شرح", "حل", "مشكلة", "خطأ"]

class TechExpertMasterFinal:
    def __init__(self):
        logging.info("--- Tech Expert Master [Fixed Path Version] ---")
        self.DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
        self.SIGNATURE = os.getenv("SIGNATURE", "").strip()
        self.DEFAULT_HASHTAGS = ["#تقنية", "#برمجة"]

        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        self.client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        self.content_pillars = {
            "الذكاء الاصطناعي": "Generative AI and AI Agents",
            "الأمن السيبراني": "Zero Trust and Cyber Security",
            "البرمجة": "Python and Modern Development"
        }

        self.system_instr = "اكتب كمختص تقني عربي بأسلوب Hook, Value, CTA. لا تضع هاشتاقات."
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"last_mention_id": None}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _generate_thread(self, pillar, details):
        prompt = f"اكتب Thread تقني عن: {pillar}. افصل بين التغريدات بـ {THREAD_DELIM}"
        resp = self.ai_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_instr},
                {"role": "user", "content": prompt}
            ]
        )
        raw = resp.choices[0].message.content
        return [p.strip() for p in raw.split(THREAD_DELIM) if p.strip()]

    def _publish_thread(self, tweets):
        prev_id = None
        for t in tweets:
            if self.DRY_RUN:
                logging.info(f"DRY RUN: {t}")
                continue
            resp = self.client_v2.create_tweet(text=t, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = resp.data["id"]
            time.sleep(2)

    def run(self):
        pillar, details = random.choice(list(self.content_pillars.items()))
        tweets = self._generate_thread(pillar, details)
        # إضافة الهاشتاق لآخر تغريدة
        tweets[-1] = f"{tweets[-1]}\n\n#تقنية #برمجة"
        self._publish_thread(tweets)
        self._save_state()

if __name__ == "__main__":
    TechExpertMasterFinal().run()
