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
TECH_KEYWORDS = ["ai", "apple", "google", "chip", "nvidia", "meta", "gpt", "ios", "android", "tech"]

# =========================
# BOT CLASS
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

    def _load_state(self):
        default = {"hashes": [], "replied_ids": [], "blacklist": [], "weekly_titles": [], "last_summary_date": ""}
        if not os.path.exists(STATE_FILE): return default
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key in default:
                    if key not in data: data[key] = default[key]
                return data
        except: return default

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def safe_gemini(self, prompt: str) -> Optional[str]:
        try:
            res = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        except Exception as e:
            logging.warning(f"Gemini Issue: {e}")
            return None

    def fallback_post(self, title: str) -> str:
        timestamp = datetime.now().strftime("%H:%M")
        return f"📍 خبر تقني مستجد [{timestamp}]:\n\n{title}\n\n#TechNews #Updates"

    def handle_weekly_summary(self):
        now = datetime.now()
        if now.weekday() == 4 and self.state["last_summary_date"] != now.strftime("%Y-%m-%d"):
            if not self.state["weekly_titles"]: return
            titles_str = "\n- ".join(self.state["weekly_titles"][-15:])
            
            # برومبت الملخص مع شرط اللغة والمصطلحات
            prompt = (
                f"أنت خبير تقني. صغ ملخصاً للأسبوع باللغة العربية بأسلوب بشري ممتع (أنسنة). "
                f"اكتب المصطلحات التقنية بالإنجليزية بجانب ترجمتها العربية. العناوين:\n{titles_str}"
            )
            
            summary = self.safe_gemini(prompt)
            if summary:
                try:
                    self.x.create_tweet(text=f"📊 حصاد الأسبوع التقني:\n\n{summary[:250]}")
                    self.state["last_summary_date"] = now.strftime("%Y-%m-%d")
                    self.state["weekly_titles"] = []
                    self._save_state()
                except: pass

    def handle_replies(self):
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me).data or []
            for tweet in mentions:
                t_id = str(tweet.id)
                if t_id in self.state["replied_ids"] or str(tweet.author_id) in self.state["blacklist"]:
                    continue
                
                # برومبت الرد مع شرط اللغة والمصطلحات
                reply_prompt = (
                    f"رد كخبير تقني لبق باللغة العربية فقط. استخدم أسلوباً بشرياً في الحوار. "
                    f"اكتب المصطلحات العلمية بالإنجليزية. النص المطلوب الرد عليه: {tweet.text}"
                )
                
                reply_text = self.safe_gemini(reply_prompt)
                if reply_text:
                    self.x.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                    self.state["replied_ids"].append(t_id)
                    self._save_state()
                    time.sleep(5)
        except: pass

    def run(self):
        logging.info("Cycle Started")
        posted = 0
        for src in SOURCES:
            feed = feedparser.parse(src)
            for entry in feed.entries[:5]:
                if posted >= MAX_POSTS: break
                title = entry.title.strip()
                h = hashlib.md5(title.encode()).hexdigest()
                if h in self.state["hashes"] or not any(k in title.lower() for k in TECH_KEYWORDS):
                    continue
                
                # برومبت النشر اليومي (أنسنة + تعريب + مصطلحات إنجليزية)
                prompt = (
                    f"أعد صياغة الخبر التالي باللغة العربية بأسلوب بشري جذاب وذكي (أنسنة). "
                    f"يجب كتابة المصطلحات التقنية الهامة باللغة الإنجليزية بين قوسين. "
                    f"الخبر: {title}"
                )
                
                text = self.safe_gemini(prompt) or self.fallback_post(title)
                try:
                    self.x.create_tweet(text=text[:280])
                    self.state["hashes"].append(h)
                    self.state["weekly_titles"].append(title)
                    self._save_state()
                    posted += 1
                    time.sleep(POST_DELAY)
                except Exception as e: logging.error(f"X Error: {e}")

        self.handle_replies()
        self.handle_weekly_summary()

if __name__ == "__main__":
    TechProfessionalBot().run()
