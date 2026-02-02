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
# GLOBAL SOURCES GRID (مصادر عالمية موثوقة)
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
    "https://www.wired.com/feed/rss"
]

STATE_FILE = "state.json"
MAX_POSTS = 2
POST_DELAY = 120

# فلاتر الاستبعاد الصارمة
BLACKLIST_TOPICS = ["war", "politics", "election", "crime", "court", "lawsuit", "military", "celebrity"]

class TechEliteFinalBot:

    def __init__(self):
        self._init_logging()
        self._load_env()
        self._init_clients()
        self.state = self._load_state()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M")

    def _load_env(self):
        # تأكد من إضافة المفاتيح في GitHub Secrets
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
            filename = "media_content.jpg"
            res = requests.get(url, stream=True, timeout=10)
            if res.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in res: f.write(chunk)
                media = self.x_api_v1.media_upload(filename)
                os.remove(filename)
                return media.media_id
        except: return None

    def safe_gemini(self, prompt: str) -> Optional[str]:
        try:
            res = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        except: return None

    def generate_content_with_verification(self, title: str, summary: str, source: str) -> Optional[str]:
        """المرحلة 1: صياغة المحتوى مع تقييد صارم للمعلومات"""
        draft_prompt = (
            f"أنت محرر تقني مدقق. حول الخبر التالي إلى تغريدة عربية بشرية محفزة.\n"
            f"الخبر: {title}\nالملخص: {summary}\n\n"
            f"⚠️ شروط عدم الهلوسة:\n"
            f"- لا تضف أي معلومة أو رقم غير موجود في النص أعلاه.\n"
            f"- حافظ على الدقة التقنية والمصطلحات الإنجليزية بين قوسين.\n"
            f"هيكل التغريدة:\n"
            f"1. بداية خاطفة (Hook).\n"
            f"2. شرح الفائدة العملية من الخبر.\n"
            f"3. نصيحة احترافية (Pro Tip) مستوحاة من النص.\n"
            f"4. سؤال تفاعلي للمتابعين + المصدر: {source}"
        )
        draft = self.safe_gemini(draft_prompt)
        if not draft: return None

        # المرحلة 2: التحقق المزدوج (Double Check)
        verify_prompt = (
            f"بصفتك مراقب جودة، قارن التغريدة بالنص الأصلي.\n"
            f"التغريدة: {draft}\n"
            f"النص الأصلي: {summary}\n\n"
            f"هل التغريدة تحتوي على معلومة واحدة (حتى لو صغيرة) غير موجودة في النص؟\n"
            f"أجب بكلمة 'سليم' للنشر، أو 'تعديل' إذا وجدت أي معلومة مختلقة."
        )
        check = self.safe_gemini(verify_prompt)
        
        return draft if check and "سليم" in check else None

    def run(self):
        logging.info("Cycle Started - Anti-Hallucination Mode")
        posted = 0
        random_sources = random.sample(SOURCES, len(SOURCES))
        
        for src in random_sources:
            feed = feedparser.parse(src)
            for entry in feed.entries[:15]:
                if posted >= MAX_POSTS: break
                
                title, summary, link = entry.title.strip(), getattr(entry, "summary", ""), entry.link
                h = hashlib.md5(title.encode()).hexdigest()

                if h in self.state["hashes"]: continue

                # فلترة المحتوى غير التقني والسياسي
                check_prompt = f"هل هذا الخبر تقني/علمي بحت وبعيد عن السياسة؟ أجب بـ نعم/لا: {title}"
                if "نعم" not in (self.safe_gemini(check_prompt) or ""): continue

                # صياغة وتحقق
                text = self.generate_content_with_verification(title, summary, urlparse(link).netloc)
                if not text:
                    logging.warning(f"⚠️ تم إلغاء تغريدة للاشتباه في دقتها: {title[:30]}")
                    continue

                try:
                    media_url = None
                    if 'media_content' in entry: media_url = entry.media_content[0]['url']
                    elif 'links' in entry:
                        for l in entry.links:
                            if 'image' in l.get('type', ''): media_url = l.get('href')
                    
                    media_id = self._upload_media(media_url)
                    self.x_client_v2.create_tweet(text=text[:280], media_ids=[media_id] if media_id else None)
                    
                    self.state["hashes"].append(h)
                    self.state["weekly_titles"].append(title)
                    self._save_state()
                    posted += 1
                    time.sleep(POST_DELAY)
                    logging.info(f"✅ تم التحقق والنشر: {title[:30]}")
                except Exception as e: logging.error(f"X Error: {e}")

if __name__ == "__main__":
    TechEliteFinalBot().run()
