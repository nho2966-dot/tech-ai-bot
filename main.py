import os
import time
import json
import hashlib
import logging
import requests
import random
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import tweepy
import feedparser
from google import genai

# =========================
# GLOBAL TECH SOURCES GRID
# =========================
SOURCES = [
    "https://ai.googleblog.com/atom.xml",
    "https://www.microsoft.com/en-us/research/feed/",
    "https://engineering.fb.com/feed/",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://www.theguardian.com/technology/rss",
    "https://www.reutersagency.com/feed/?best-topics=technology&post_type=best",
    "https://www.technologyreview.com/feed/",
    "https://spectrum.ieee.org/rss/fulltext",
    "https://arstechnica.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://gizmodo.com/rss"
]

STATE_FILE = "state.json"
MAX_POSTS = 2 
POST_DELAY = 120 

class TechEliteFinalBot:

    def __init__(self):
        self._init_logging()
        self._load_env()
        self._init_clients()
        self.state = self._load_state()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M")

    def _load_env(self):
        self.GEMINI_KEY = os.getenv("GEMINI_KEY")
        self.X_API_KEY = os.getenv("X_API_KEY")
        self.X_API_SECRET = os.getenv("X_API_SECRET")
        self.X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
        self.X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
        self.X_BEARER = os.getenv("X_BEARER_TOKEN")

    def _init_clients(self):
        self.ai = genai.Client(api_key=self.GEMINI_KEY)
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
        default = {"hashes": [], "replied_ids": [], "blacklist": [], "weekly_titles": [], "last_summary_date": ""}
        if not os.path.exists(STATE_FILE): return default
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except: return default

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _upload_media(self, url: str) -> Optional[str]:
        if not url: return None
        try:
            filename = "media_item.jpg"
            res = requests.get(url, stream=True, timeout=10)
            if res.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in res: f.write(chunk)
                media = self.x_api_v1.media_upload(filename)
                if os.path.exists(filename): os.remove(filename)
                return media.media_id
        except Exception as e:
            logging.error(f"Media Upload Error: {e}")
        return None

    def safe_ai_request(self, title: str, summary: str, source: str) -> Optional[str]:
        prompt = (
            f"حلل الخبر التقني التالي بعناية شديدة:\n"
            f"العنوان: {title}\nالمصادر: {summary
