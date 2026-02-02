import os
import time
import json
import hashlib
import logging
import requests
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import tweepy
import feedparser
from google import genai

# =========================
# CONFIGURATION
# =========================

SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://9to5mac.com/feed/",
]

STATE_FILE = "state.json"
MAX_POSTS = 2 
POST_DELAY = 60

BLACKLIST_TOPICS = ["politics", "war", "crime", "celebrity", "gossip", "election", "military", "sports"]
TECH_KEYWORDS = ["ai", "apple", "google", "chip", "nvidia", "meta", "gpt", "ios", "android", "software", "hardware"]

class TechEliteBot:

    def __init__(self):
        self._init_logging()
        self._load_env()
        self._init_clients()
        self.state = self._load_state()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🚀 %(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M")

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
            filename = "temp_res.jpg"
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

    def analyze_and_format(self, title: str, summary: str, source: str) -> Optional[str]:
        """المحرك الإبداعي: صياغة التغريدة بنظام الطبقات الثلاث"""
        prompt = (
            f"أنت خبير تقني ومحلل استراتيجي بمتابعة عالمية. حلل الخبر الآتي بصيغة 'أنسنة' جذابة:\n"
            f"العنوان: {title}\nالملخص: {summary}\n\n"
            f"المطلوب صياغة تغريدة احترافية تلتزم بالآتي:\n"
            f"1. ابدأ بوسم حالة مناسب مثل (🚀 إطلاق رسمي، 🕵️ تسريب، 💡 فكرة، 🔄 تحديث).\n"
            f"2. الطبقة الأولى: ابدأ بسؤال تفاعلي يمس المتابع مباشرة.\n"
            f"3. الطبقة الثانية: اشرح الخبر والفوائد العملية منه مع ذكر المصطلحات التقنية بالإنجليزية بين قوسين.\n"
            f"4. الطبقة الثالثة: قدم 'نظرة مستقبلية' أو توقع ذكي بناءً على هذا الخبر.\n"
            f"5. الخاتمة: دعوة للمشاركة + المصدر: {source}\n\n"
            f"⚠️ ملاحظة: ممنوع اختلاق حقائق، وممنوع استخدام الإنجليزية إلا للمصطلحات."
        )
        return self.safe_gemini(prompt)

    def run(self):
        logging.info("Cycle Started - Elite Analysis Mode")
        posted = 0
        for src in SOURCES:
            feed = feedparser.parse(src)
            for entry in feed.entries[:10]:
                if posted >= MAX_POSTS: break
                title, summary, link = entry.title.strip(), getattr(entry, "summary", ""), entry.link
                h = hashlib.md5(title.encode()).hexdigest()

                if h in self.state["hashes"]: continue
                
                # فحص السياسة والمحتوى غير التقني
                check_prompt = f"هل هذا الخبر تقني بحت ولا علاقة له بالسياسة أو القضايا العامة؟ أجب بـ 'نعم' أو 'لا' فقط: {title}"
                is_tech = self.safe_gemini(check_prompt)
                if not is_tech or "نعم" not in is_tech: continue

                media_url = None
                if 'media_content' in entry: media_url = entry.media_content[0]['url']
                
                # صياغة المحتوى الاحترافي
                text = self.analyze_and_format(title, summary, urlparse(link).netloc)
                if not text or not any('\u0600' <= c <= '\u06FF' for c in text): continue

                try:
                    media_id = self._upload_media(media_url)
                    self.x_client_v2.create_tweet(text=text[:280], media_ids=[media_id] if media_id else None)
                    
                    self.state["hashes"].append(h)
                    self.state["weekly_titles"].append(title)
                    self._save_state()
                    posted += 1
                    time.sleep(POST_DELAY)
                except Exception as e: logging.error(f"X Error: {e}")

        # الردود الذكية والملخص الأسبوعي
        self.handle_replies()
        self.handle_summary()

    # (هنا تضاف دوال handle_replies و handle_summary من النسخة السابقة)
    # ... سأختصرها لضمان عمل الكود الرئيسي ...
