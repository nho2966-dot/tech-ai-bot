import os
import sqlite3
import hashlib
import json
import time
import random
import re
import numpy as np
from datetime import datetime
import tweepy
import feedparser
import requests
from dotenv import load_dotenv
from openai import OpenAI
import logging

load_dotenv()

# إعدادات محسنة لـ GitHub Actions
CONFIG = {
    "DB": "sovereign_v550.db",
    "SIM_THRESHOLD": 0.88,
    "POLL_CHANCE": 0.40,
    "QUIZ_CHANCE": 0.20,
    "MAX_REPLIES": 3,
    "DAILY_MAX_TWEETS": 8,          # ابدأ بـ 8 فقط في Actions
    "REPLY_DELAY": 60               # تأخير ثابت آمن
}

RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SovereignGithubBot")

class SovereignGithubBot:
    def __init__(self):
        self.embedding_dim = 1536
        self._init_db()
        try:
            self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True  # ← مهم جدًا هنا
            )
            me = self.x.get_me()
            self.bot_id = str(me.data.id) if me and me.data else None
            if not self.bot_id:
                raise Exception("فشل التحقق من الهوية")
            logger.info(f"تم تسجيل الدخول - ID: {self.bot_id}")
        except Exception as e:
            logger.critical(f"فشل الاتصال: {e}")
            exit(1)

        self.sources = [
            "https://www.arabnews.com/rss/technology",
            "https://www.zawya.com/en/rss/technology",
            "https://www.alkhaleej.ae/rss/technology",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://hackernoon.com/feed/tag/ai"
        ]

    def _init_db(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, score REAL, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, user_id TEXT)")
            c.commit()

    def _get_meta(self, key, default="0"):
        with sqlite3.connect(CONFIG["DB"]) as c:
            row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def _update_meta(self, key, value):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, str(value)))
            c.commit()

    def _brain(self, content="", mode="POST"):
        system_rules = (
            "أنت مستشار تقني خليجي رصين. ركز على (HUMAIN OS)، (الوكلاء الشخصيين)، (السيادة الرقمية). "
            "في POLL: سطر أول = السؤال، ثم 4 خيارات قصيرة (أقل من 24 حرف). "
            "لا هلوسة، لا أخبار شركات غربية. أنهِ بسؤال تفاعلي."
        )
        prompts = {
            "POST": f"حلل للفرد بأسلوب جدلي: {content}",
            "REPLY": f"رد محترف خليجي يثير الجدل وأنهِ بسؤال: {content}",
            "QUIZ": "سؤال ذكي واحد عن السيادة الرقمية أو HUMAIN OS.",
            "POLL": "استطلاع رأي عن الوكلاء الذكيين أو السيادة. السؤال سطر، ثم 4 خيارات."
        }
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompts[mode]}],
                timeout=30
            )
            return f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"
        except Exception as e:
            logger.error(f"خطأ في _brain ({mode}): {e}")
            return ""

    def fetch(self):
        logger.info("جاري جلب الأخبار...")
        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:5]:
                    title = (e.title or "").strip()
                    if not title: continue
                    if any(x in title.lower() for x in ["stock", "revenue", "acquisition", "ceo"]): continue
                    h = hashlib.sha256(title.encode()).hexdigest()
                    with sqlite3.connect(CONFIG["DB"]) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title, score) VALUES (?,?,?)", (h, title, 4.0))
                        c.commit()
            except Exception as e:
                logger.warning(f"فشل جلب {src}: {e}")

    def handle_interactions(self):
        last_id = int(self._get_meta("last_mention_id", "1"))
        try:
            mentions = self.x.get_users_mentions(
                id=self.bot_id,
                since_id=last_id,
                max_results=CONFIG["MAX_REPLIES"]
            )
            if not mentions.data: return

            new_last_id = last_id
            for m in mentions.data:
                tweet_id = str(m.id)
                new_last_id = max(new_last_id, m.id)
                with sqlite3.connect(CONFIG["DB"]) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (tweet_id,)).fetchone():
                        continue

                    reply = self._brain(m.text, mode="REPLY")
                    if reply:
                        try:
                            self.x.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet_id)
                            c.execute("INSERT INTO replies VALUES (?,?)", (tweet_id, str(m.author_id)))
                            c.commit()
                            logger.info(f"تم الرد على {tweet_id}")
                            time.sleep(CONFIG["REPLY_DELAY"])
                        except tweepy.TooManyRequests:
                            logger.warning("Rate limit في الردود - تخطي")
                            break
            self._update_meta("last_mention_id", str(new_last_id))
        except Exception as e:
            logger.error(f"خطأ في المنشنز: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count_key = f"daily_count_{today}"
        count = int(self._get_meta(count_key, "0"))
        if count >= CONFIG["DAILY_MAX_TWEETS"]:
            logger.info(f"الحد اليومي مكتمل ({count}/{CONFIG['DAILY_MAX_TWEETS']})")
            return

        rand = random.random()
        try:
            if rand < CONFIG["QUIZ_CHANCE"]:
                text = self._brain("", "QUIZ")
                if text:
                    self.x.create_tweet(text=text[:280])
                    logger.info("نُشرت مسابقة")
            elif rand < (CONFIG["QUIZ_CHANCE"] + CONFIG["POLL_CHANCE"]):
                raw = self._brain("", "POLL")
                lines = [l.strip() for l in raw.split('\n') if l.strip()]
                if len(lines) < 2:
                    return
                poll_text = lines[0][:280]
                options = [l[:24] for l in lines[1:5] if l.strip()]
                if len(options) < 2:
                    options = ["سيادة محلية", "سحابة قوية", "لا أثق", "تجربة أولاً"]
                self.x.create_tweet(text=poll_text, poll_options=options[:4], poll_duration_minutes=1440)
                logger.info("نُشر استطلاع")
            else:
                with sqlite3.connect(CONFIG["DB"]) as c:
                    row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' LIMIT 1").fetchone()
                    if row:
                        content = self._brain(row[1], "POST")
                        if content:
                            self.x.create_tweet(text=content[:280])
                            c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row[0],))
                            c.commit()
                            logger.info("نُشر خبر/تحليل")
            self._update_meta(count_key, str(count + 1))
        except tweepy.TooManyRequests:
            logger.warning("Rate limit في النشر - تخطي")
        except Exception as e:
            logger.error(f"خطأ في dispatch: {e}")

    def run_once(self):
        wait = random.randint(30, 300)  # تأخير أقصر لـ Actions
        logger.info(f"انتظار {wait} ثانية قبل البدء...")
        time.sleep(wait)
        self.fetch()
        self.handle_interactions()
        self.dispatch()
        logger.info("انتهت دورة GitHub Actions.")

if __name__ == "__main__":
    bot = SovereignGithubBot()
    bot.run_once()
