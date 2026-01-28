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

logging.basicConfig(level=logging.INFO, format="%(message)s")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

# إعدادات البحث والأخبار
AI_RSS_FEEDS = ["https://techcrunch.com/tag/ai/feed/", "https://www.technologyreview.com/feed/"]
TECH_TRIGGERS = ["كيف", "لماذا", "ما", "حل", "مشكلة", "خطأ", "برمجة", "تقنية"]
ROTATION_KINDS = ["breaking_news", "ai_daily_life", "ai_tool"]

# Regex لتنظيف النصوص
URL_RE = re.compile(r"https?://\S+")
HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)

def sanitize_text(text: str) -> str:
    t = HASHTAG_RE.sub(lambda m: m.group(1), text)
    return t.strip()

class TechExpertMasterFinal:
    def __init__(self):
        logging.info("--- Tech Expert Master Pro [v88.3] ---")
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

    def fetch_news(self):
        items = []
        for feed in AI_RSS_FEEDS:
            try:
                r = requests.get(feed, timeout=10)
                root = ET.fromstring(r.content)
                for item in root.findall('.//item')[:3]:
                    items.append(f"• {item.find('title').text}")
            except: continue
        return items

    def handle_smart_replies(self):
        query = random.choice(TECH_TRIGGERS)
        tweets = self.client_v2.search_recent_tweets(query=f"{query} -is:retweet", max_results=5)
        if tweets.data:
            for tweet in tweets.data:
                if tweet.id not in self.state["replied_to"]:
                    prompt = f"اكتب رداً تقنياً ذكياً ومفيداً جداً باللغة العربية: '{tweet.text}'"
                    res = self.ai_client.chat.completions.create(
                        model="openai/gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    reply = sanitize_text(res.choices[0].message.content)
                    self.client_v2.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"Replied to: {tweet.id}")
                    break

    def post_content(self):
        kind = ROTATION_KINDS[self.state["rotation_idx"] % len(ROTATION_KINDS)]
        self.state["rotation_idx"] += 1
        
        if kind == "breaking_news":
            news = self.fetch_news()
            prompt = f"اكتب ثريد تقني عربي من 3 تغريدات بناءً على هذه الأخبار: {news}. افصل بـ {THREAD_DELIM}"
        elif kind == "ai_tool":
            prompt = "اكتب تغريدة عن أداة ذكاء اصطناعي مفيدة جداً للمصممين أو المبرمجين."
        else:
            prompt = "اكتب نصيحة تقنية مذهلة لتطوير المسار المهني في البرمجة."

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
        try:
            self.handle_smart_replies()
            time.sleep(10)
            self.post_content()
            self._save_state()
        except Exception as e:
            logging.error(f"Error: {e}")

if __name__ == "__main__":
    TechExpertMasterFinal().run()
