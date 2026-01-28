import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone

import tweepy
from openai import OpenAI

# إعداد المسارات لضمان العمل داخل مجلد tech-ai-bot
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
AUDIT_LOG = os.path.join(BASE_DIR, "audit_log.jsonl")

logging.basicConfig(level=logging.INFO, format="%(message)s")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)

TECH_TRIGGERS = [
    "كيف", "لماذا", "ما", "وش", "أفضل", "شرح", "حل", "مشكلة", "خطأ",
    "error", "bug", "issue", "api", "python", "javascript", "rust",
    "ai", "security", "blockchain", "cloud", "aws", "grok", "gpt"
]

class TechExpertMasterFinal:
    def __init__(self):
        logging.info("--- Tech Expert Master [v88.0 Fixed] ---")
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
            "الذكاء الاصطناعي": "Generative AI, AI Agents, ChatGPT/Grok/Copilot",
            "الأمن السيبراني": "Zero Trust, Passkeys, Ransomware",
            "البرمجة": "Python/Rust, AI Tools, Clean Code",
            "الحوسبة السحابية": "AWS/Azure/GCP, Cloud Security"
        }

        self.system_instr = (
            "اكتب كمختص تقني عربي بأسلوب واضح ومختصر.\n"
            "التزم بالهيكلة الذهبية: Hook ثم Value ثم CTA (سؤال).\n"
            "لا تضف هاشتاقات داخل النص.\n"
        )
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

    def _audit(self, event_type, payload):
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "payload": payload
        }
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _apply_hashtags_to_last_tweet(self, tweets, max_tags=2):
        last_tweet = tweets[-1]
        tag_line = " ".join(self.DEFAULT_HASHTAGS[:max_tags])
        tweets[-1] = f"{last_tweet}\n\n{tag_line}".strip()
        return tweets

    def _generate_thread(self, pillar, details):
        prompt = f"اكتب Thread تقني عن: {pillar} ({details}). افصل بـ {THREAD_DELIM}"
        resp = self.ai_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
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
                logging.info(f"[DRY] {t}")
                continue
            resp = self.client_v2.create_tweet(text=t, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = resp.data["id"]
            time.sleep(2)
        return True

    def run(self):
        pillar, details = random.choice(list(self.content_pillars.items()))
        raw_tweets = self._generate_thread(pillar, details)
        final_tweets = self._apply_hashtags_to_last_tweet(raw_tweets)
        self._publish_thread(final_tweets)
        self._save_state()
        logging.info("✅ Done.")

if __name__ == "__main__":
    TechExpertMasterFinal().run()
