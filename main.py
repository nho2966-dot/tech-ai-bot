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
        # تم إصلاح القوس المفقود في السطر التالي
        prompt = (
            f"حلل الخبر التقني التالي بعناية:\n"
            f"العنوان: {title}\n"
            f"المحتوى: {summary}\n\n"
            f"مهمتك:\n"
            f"1. استبعد أي محتوى غير تقني أو سياسي بكلمة 'تخطي'.\n"
            f"2. صغ تغريدة عربية بشرية (Hook + حقيقة تقنية دقيقة + Pro Tip + سؤال تفاعلي).\n"
            f"3. المصطلحات بالإنجليزية بين قوسين والمصدر: {source}\n"
            f"⚠️ التزم بالحقائق المذكورة فقط لمنع الهلوسة."
        )
        try:
            time.sleep(2)
            res = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            output = res.text.strip()
            if "تخطي" in output or len(output) < 30: return None
            return output
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def run(self):
        logging.info("Cycle Started - Anti-Hallucination Fixed Mode")
        posted = 0
        random_sources = random.sample(SOURCES, len(SOURCES))
        
        for src in random_sources:
            if posted >= MAX_POSTS: break
            feed = feedparser.parse(src)
            
            for entry in feed.entries[:10]:
                if posted >= MAX_POSTS: break
                
                title = entry.title.strip()
                summary = getattr(entry, "summary", "")
                h = hashlib.md5(title.encode()).hexdigest()

                if h in self.state["hashes"]: continue

                tweet_text = self.safe_ai_request(title, summary, urlparse(entry.link).netloc)
                
                if tweet_text:
                    try:
                        media_url = None
                        if 'media_content' in entry: media_url = entry.media_content[0]['url']
                        elif 'links' in entry:
                            for l in entry.links:
                                if 'image' in l.get('type', ''): media_url = l.get('href')
                        
                        media_id = self._upload_media(media_url)
                        self.x_client_v2.create_tweet(text=tweet_text[:280], media_ids=[media_id] if media_id else None)
                        
                        self.state["hashes"].append(h)
                        self._save_state()
                        posted += 1
                        logging.info(f"✅ Published: {title[:30]}")
                        time.sleep(POST_DELAY)
                    except Exception as e:
                        logging.error(f"X Error: {e}")

if __name__ == "__main__":
    TechEliteFinalBot().run()
