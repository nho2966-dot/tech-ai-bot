import os
import time
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional

import tweepy
import feedparser
from google import genai

# =========================
# SETTINGS
# =========================

SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://9to5mac.com/feed/",
]

STATE_FILE = "state.json"
MAX_POSTS = 2
POST_DELAY = 60

# =========================
# BOT
# =========================

class TechProfessionalBot:

    def __init__(self):
        self._init_logging()
        self._load_env()
        self._init_clients()
        self.state = self._load_state()

    def _init_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="🚀 Tech Newsroom | %(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M"
        )

    def _load_env(self):
        self.GEMINI_KEY = os.getenv("GEMINI_KEY")
        self.X_API_KEY = os.getenv("X_API_KEY")
        self.X_API_SECRET = os.getenv("X_API_SECRET")
        self.X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
        self.X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
        self.X_BEARER = os.getenv("X_BEARER_TOKEN")

    def _init_clients(self):
        self.ai = genai.Client(api_key=self.GEMINI_KEY)

        self.x = tweepy.Client(
            bearer_token=self.X_BEARER,
            consumer_key=self.X_API_KEY,
            consumer_secret=self.X_API_SECRET,
            access_token=self.X_ACCESS_TOKEN,
            access_token_secret=self.X_ACCESS_SECRET
        )

    # =========================
    # STATE
    # =========================

    def _load_state(self):
        if not os.path.exists(STATE_FILE):
            return {"hashes": []}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"hashes": []}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    # =========================
    # SAFE AI
    # =========================

    def safe_gemini(self, prompt: str) -> Optional[str]:
        try:
            res = self.ai.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return res.text.strip()
        except Exception as e:
            logging.warning(f"Gemini unavailable → fallback used ({e})")
            return None

    # =========================
    # FALLBACK (NO AI)
    # =========================

    def fallback_post(self, title: str) -> str:
        return f"خبر تقني جديد:\n{title}\n\n#Technology #TechNews"

    # =========================
    # NEWS
    # =========================

    def fetch_news(self):
        items = []
        seen = set()

        for src in SOURCES:
            feed = feedparser.parse(src)
            for entry in feed.entries[:5]:
                title = entry.title.strip()
                if title.lower() in seen:
                    continue
                items.append(entry)
                seen.add(title.lower())

        return items

    # =========================
    # RUN
    # =========================

    def run(self):
        logging.info("Bot started")

        posted = 0
        for item in self.fetch_news():
            if posted >= MAX_POSTS:
                break

            h = hashlib.md5(item.title.encode()).hexdigest()
            if h in self.state["hashes"]:
                continue

            prompt = (
                "أعد صياغة الخبر بأسلوب تقني مهني مختصر بدون مبالغة:\n"
                f"{item.title}"
            )

            text = self.safe_gemini(prompt)
            if not text:
                text = self.fallback_post(item.title)

            text = text[:280]

            try:
                self.x.create_tweet(text=text)
                self.state["hashes"].append(h)
                self._save_state()
                posted += 1
                time.sleep(POST_DELAY)
            except Exception as e:
                logging.error(f"X post failed: {e}")

        logging.info("Cycle completed")

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    TechProfessionalBot().run()
