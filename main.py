import os
import sqlite3
import hashlib
import logging
import time
import random
from datetime import datetime, date, timedelta
from collections import deque
from typing import Optional, List, Dict, Any

import tweepy
from openai import OpenAI
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import feedparser
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO, format="🛡️ [نظام السيادة]: %(message)s")


class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()
        self.reply_timestamps = deque(maxlen=50)
        self.replied_tweets_cache: set = set()
        self.last_mention_id: Optional[int] = None

        # قائمة RSS Feeds الموسعة (عالمية + عربية + مصرية + محلية خليجية)
        self.rss_feeds = [
            # ── عالمية (أساسية) ──
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/",
            "https://www.wired.com/feed/category/science/latest/rss",
            "https://arstechnica.com/category/tech/feed/",
            "https://www.engadget.com/rss.xml",
            "https://www.cnet.com/rss/news/",
            "https://www.technologyreview.com/feed/",
            "https://gizmodo.com/rss",
            "https://venturebeat.com/feed/",
            "https://thenextweb.com/feed",
            "https://www.artificialintelligence-news.com/feed/",
            "https://huggingface.co/blog/feed.xml",
            "https://www.deepmind.com/blog/rss.xml",
            "https://openai.com/blog/rss/",

            # ── عربية عامة ──
            "https://www.tech-wd.com/wd-rss-feed.xml",
            "https://www.aitnews.com/feed/",
            "https://www.arageek.com/feed/tech",
            "https://arabhardware.net/feed",
            "https://www.tqniah.net/feed/",
            "https://www.arabtechs.net/feed",
            "https://www.taqniah.com/feed/",

            # ── مصرية (تقنية وأخبار عامة مع تركيز تقني) ──
            "https://www.youm7.com/rss/Technologia",               # اليوم السابع – قسم تكنولوجيا
            "https://www.almasryalyoum.com/rss",                   # المصري اليوم – تغطية تقنية
            "https://www.masrawy.com/rss/tech",                    # مصراوي – قسم تكنولوجيا
            "https://www.elbalad.news/rss/tech",                   # البوابة نيوز – تقنية
            "https://www.elwatannews.com/rss/section/6",           # الوطن – قسم تكنولوجيا
            "https://www.dostor.org/rss/technology",               # الدستور – تقنية
            "https://www.vetogate.com/rss/technology",             # فيتو – تقنية
            "https://www.cairo24.com/rss/technology",              # القاهرة 24 – تقنية

            # ── محلية خليجية (سعودية، إماراتية، قطرية...) ──
            "https://sabq.org/feed",
            "https://www.aleqt.com/feed",
            "https://aawsat.com/rss/technologia",
            "https://www.okaz.com.sa/rss",
            "https://www.alriyadh.com/page/rss",
            "https://www.alyaum.com/rss",
            "https://www.albayan.ae/tech/rss",
            "https://www.emaratalyoum.com/rss/tech",
            "https://wam.ae/feed/technology",
            "https://qna.org.qa/ar-QA/RSS-Feeds/Technology",
            "https://www.alanba.com.kw/rss/tech",
            "https://kuwaitalyawm.media.gov.kw/rss",
            "https://www.bna.bh/rss",
            "https://omannews.gov.om/rss/technology",
        ]

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            c.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS replied_tweets (tweet_id TEXT PRIMARY KEY, ts DATETIME)")

    def _setup_clients(self):
        try:
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        except Exception as e:
            logging.error(f"فشل تهيئة Gemini: {e}")
            self.gemini_client = None

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        try:
            me = self.x_client.get_me(user_auth=True)
            self.my_user_id = me.data.id
            logging.info(f"Bot user ID: {self.my_user_id}")
        except Exception as e:
            logging.error(f"فشل جلب user ID: {e}")
            self.my_user_id = None

        self.llm_clients = {
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"),
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=5, max=45),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def generate_text(self, prompt: str, system_msg: str) -> str:
        sequence = [
            ("xAI Grok", "xAI", "grok-4-1-fast-reasoning"),
            ("Groq Llama", "Groq", "llama-3.3-70b-versatile"),
            ("Gemini Flash", "Gemini", "gemini-2.5-flash"),
            ("OpenAI 4o-mini", "OpenAI", "gpt-4o-mini"),
        ]

        for name, key, model in sequence:
            try:
                client = self.llm_clients.get(key) if key != "Gemini" else self.gemini_client
                if not client:
                    continue

                if key == "Gemini":
                    m = client.GenerativeModel(model)
                    res = m.generate_content(f"{system_msg}\n{prompt}")
                    text = res.text.strip()
                else:
                    res = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.82,
                        max_tokens=420,
                        timeout=40
                    )
                    text = res.choices[0].message.content.strip()

                if text and len(text) > 80:
                    return text

            except Exception as e:
                logging.warning(f"{name} فشل: {str(e)[:100]}")
                continue

        raise RuntimeError("فشل كل النماذج")

    def already_posted(self, content: str) -> bool:
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            return bool(conn.execute("SELECT 1 FROM history WHERE hash = ?", (h,)).fetchone())

    def mark_posted(self, content: str):
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO history (hash, ts) VALUES (?, datetime('now'))", (h,))

    def fetch_fresh_rss(self, max_per_feed: int = 3, max_age_hours: int = 48) -> List[Dict]:
        articles = []
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        ua = "SovereignBot/1.0 (Arabic Tech News Bot)"

        for url in self.rss_feeds:
            try:
                feed = feedparser.parse(url
