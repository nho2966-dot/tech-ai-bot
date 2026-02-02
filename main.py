import os
import time
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional

import feedparser
import tweepy
import requests
from dotenv import load_dotenv

# ================== CONFIG ==================
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MAX_AI_FAILURES = 3
AI_BACKOFF_BASE = 15  # seconds
CACHE_FILE = "ai_cache.json"

RSS_FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://www.deepmind.com/blog/rss.xml",
    "https://ai.googleblog.com/feeds/posts/default",
    "https://www.theverge.com/ai/rss/index.xml",
]

TECH_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "machine learning",
    "gpu", "chip", "processor", "nvidia", "amd",
    "robot", "automation", "neural", "model"
]

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format="🛡️ %(asctime)s | %(message)s"
)

# ================== CACHE ==================
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

CACHE = load_cache()

# ================== UTILS ==================
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def is_technical(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in TECH_KEYWORDS)

# ================== AI ==================
def ask_gemini(prompt: str) -> Optional[str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    r = requests.post(url, json=payload, timeout=15)
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    elif r.status_code == 429:
        logging.warning("Gemini rate limit hit.")
        return None
    else:
        logging.error(f"Gemini error: {r.text}")
        return None

def ask_openrouter(prompt: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Tech AI Bot"
    }

    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [
            {"role": "system", "content": "You are a professional technology news analyst."},
            {"role": "user", "content": prompt}
        ]
    }

    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=20
    )

    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    else:
        logging.error(f"OpenRouter error: {r.text}")
        return None

def ai_analyze(text: str) -> Optional[str]:
    h = hash_text(text)
    if h in CACHE:
        return CACHE[h]

    prompt = f"""
Summarize this news professionally in Arabic.
Only if it is verified technical AI or hardware news.
If not technical, reply with: SKIP

{text}
"""

    failures = 0
    backoff = AI_BACKOFF_BASE

    # Try Gemini
    res = ask_gemini(prompt)
    if res:
        CACHE[h] = res
        save_cache(CACHE)
        return res

    # Fallback OpenRouter
    res = ask_openrouter(prompt)
    if res:
        CACHE[h] = res
        save_cache(CACHE)
        return res

    return None

# ================== TWITTER ==================
auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET")
)
twitter = tweepy.API(auth)

# ================== MAIN ==================
def run():
    logging.info("Scanning feeds...")
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:3]:
            text = f"{entry.title}\n{entry.summary}"

            if not is_technical(text):
                continue

            analysis = ai_analyze(text)
            if not analysis or "SKIP" in analysis:
                continue

            tweet = f"{analysis[:260]}\n\n🔗 {entry.link}"
            twitter.update_status(tweet)
            logging.info("Tweet posted.")
            time.sleep(30)

if __name__ == "__main__":
    run()
