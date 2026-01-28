import os
import re
import json
import time
import random
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

import tweepy
from openai import OpenAI

# إعداد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
AUDIT_LOG = os.path.join(BASE_DIR, "audit_log.jsonl")
TEMPLATES_FILE = os.path.join(BASE_DIR, "templates_ar.json")

logging.basicConfig(level=logging.INFO, format="%(message)s")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

# إعدادات الاستهداف والأخبار (بناءً على هيكلك)
TECH_TRIGGERS = ["كيف", "لماذا", "ما", "حل", "مشكلة", "خطأ", "برمجة", "تقنية"]
AI_RSS_FEEDS = ["https://techcrunch.com/tag/ai/feed/", "https://www.technologyreview.com/feed/"]
ROTATION_KINDS = ["breaking_news", "ai_daily_life", "ai_tool"]

# --- دوال المساعدة وهيكل التنظيف ---
def sanitize_text(text: str) -> str:
    # إزالة الهاشتاقات والميشنات المزعجة بناءً على هيكلك
    t = re.sub(r"(?<!\w)#([\w_]+)", r"\1", text)
    t = re.sub(r"(^|\s)@(\w{1,15})", r"\1\2", t)
    return t.strip()

def audit(event_type: str, payload: dict):
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "type": event_type, "payload": payload}
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# --- محرك البحث والجلب ---
def fetch_ai_headlines():
    items = []
    for feed in AI_RSS_FEEDS:
        try:
            r = requests.get(feed, timeout=12)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:3]:
                title = item.find('title').text
                link = item.find('link').text
                items.append({"title": title, "url": link, "source": urlparse(link).netloc})
        except: continue
    return items

class TechExpertDiversifiedPro:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Full Hybrid Mode] ---")
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
        self.client_v2 = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_SECRET"],
            wait_on_rate_limit=True
        )
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data.setdefault("replied_to", [])
                    data.setdefault("rotation_idx", 0)
                    return data
            except: pass
        return {"replied_to": [], "rotation_idx": 0}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # --- مهمة الردود الذكية (Targeting) ---
    def handle_smart_replies(self):
        query = random.choice(TECH_TRIGGERS)
        try:
            tweets = self.client_v2.search_recent_tweets(query=f"{query} -is:retweet", max_results=5, lang="ar")
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id not in self.state["replied_to"]:
                        prompt = f"اكتب رداً تقنياً ذكياً ومفيداً (Hook-Value-CTA) على: '{tweet.text}'"
                        res = self.ai_client.chat.completions.create(
                            model="openai/gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        reply = sanitize_text(res.choices[0].message.content)
                        self.client_v2.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                        self.state["replied_to"].append(tweet.id)
                        audit("smart_reply", {"tweet_id": tweet.id})
                        break
        except Exception as e: logging.error(f"Reply Error: {e}")

    # --- مهمة النشر المتنوع (Rotation) ---
    def execute_diversified_task(self):
        kind = ROTATION_KINDS[self.state["rotation_idx"] % len(ROTATION_KINDS)]
        self.state["rotation_idx"] += 1
        
        context_news = ""
        if kind == "breaking_news":
            news = fetch_ai_headlines()
            context_news = "\n".join([f"- {n['title']}" for n in news])

        prompt = f"اكتب محتوى تقني نوع ({kind}) بناءً على المعلومات التالية: {context_news}. " \
                 f"إذا كان المحتوى طويلاً افصل بين التغريدات بـ {THREAD_DELIM}. الأسلوب: Hook قوي وقيمة عملية."

        res = self.ai_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        content = res.choices[0].message.content

        if THREAD_DELIM in content:
            parts = [sanitize_text(p) for p in content.split(THREAD_DELIM)]
            prev_id = None
            for p in parts:
                resp = self.client_v2.create_tweet(text=p[:280], in_reply_to_tweet_id=prev_id)
                prev_id = resp.data["id"]
                time.sleep(2)
        else:
            self.client_v2.create_tweet(text=sanitize_text(content)[:280])

    def run(self):
        self.handle_smart_replies() # رد ذكي واحد
        time.sleep(10)
        self.execute_diversified_task() # ثريد أو تغريدة حسب التدوير
        self._save_state()

if __name__ == "__main__":
    TechExpertDiversifiedPro().run()
