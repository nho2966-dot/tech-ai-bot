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
from logging.handlers import RotatingFileHandler

load_dotenv()

# --- ميثاق العمل والضوابط الصارمة ---
CONFIG = {
    "DB": "sovereign_v550.db",
    "COOLDOWN_MINUTES": 90,
    "SIM_THRESHOLD": 0.88,
    "PEAK_HOURS": [9, 10, 13, 17, 18, 19, 20, 21, 22],
    "POLL_CHANCE": 0.30,  # رفع النسبة لزيادة الضجة والجدل
    "QUIZ_CHANCE": 0.15,
    "MAX_REPLIES": 5,
    "DAILY_MAX_TWEETS": 10,  # حد أقصى يومي لتجنب السبام
    "REPLY_DELAY_MIN": 8,    # تأخير بشري للردود
    "REPLY_DELAY_MAX": 25
}

RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

# إعداد الـ logging
logger = logging.getLogger("SovereignBot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("sovereign_v550.log", maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s | %(levelname)7s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())  # يطبع في الـ console أيضاً

class SovereignControversyV550:
    def __init__(self):
        self.embedding_dim = None  # سيتم تعيينها ديناميكياً
        self._init_db()
        self._init_clients()
        # مصادر تركز على الوكلاء، الخصوصية، والتقنيات الجدلية
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://hackernoon.com/feed",
            "https://www.wired.com/feed/category/gear/latest/rss",
            "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
            "https://aisupremacy.substack.com/feed"  # مصدر نخبوية للذكاء الاصطناعي
        ]
        self.daily_tweet_count = 0  # عداد يومي للتغريدات

    def _init_db(self):
        try:
            with sqlite3.connect(CONFIG["DB"]) as c:
                c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, embedding TEXT)")
                c.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, h TEXT UNIQUE, title TEXT, score REAL, status TEXT DEFAULT 'PENDING', created_at TEXT)")
                c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
                c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, user_id TEXT, created_at TEXT)")
                c.commit()
            logger.info("قاعدة البيانات جاهزة")
        except Exception as e:
            logger.error(f"خطأ في إنشاء DB: {e}")

    def _init_clients(self):
        try:
            self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True  # يتعامل تلقائياً مع rate limits
            )
            self.bot_id = self.x.get_me().data.id
            logger.info(f"البوت جاهز، ID: {self.bot_id}")
        except Exception as e:
            logger.error(f"خطأ في تهيئة العملاء: {e}")
            self.bot_id = None

    def _embedding(self, text):
        try:
            res = self.ai.embeddings.create(model="text-embedding-3-small", input=text)
            emb = res.data[0].embedding
            if self.embedding_dim is None:
                self.embedding_dim = len(emb)
            return np.array(emb)
        except Exception as e:
            logger.warning(f"فشل في جلب embedding: {e}")
            dim = self.embedding_dim or 1536
            return np.zeros(dim)

    def _cosine(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _is_semantic_duplicate(self, emb):
        with sqlite3.connect(CONFIG["DB"]) as c:
            rows = c.execute("SELECT embedding FROM memory").fetchall()
        for r in rows:
            old_emb = np.array(json.loads(r[0]))
            if self._cosine(emb, old_emb) > CONFIG["SIM_THRESHOLD"]:
                return True
        return False

    def _brain(self, content, mode="POST"):
        # دستور التحليل: الكيفية، التطبيق، الفائدة، المقارنة، والجدل
        system_rules = (
            "أنت مستشار تقني خليجي نخبوي. لغتك (خليجية بيضاء رصينة). "
            "ممنوع الحديث عن أخبار الشركات والمؤسسات. ركز حصراً على الفرد وسيادته الرقمية. "
            "تحدث عن بناء (الوكلاء الشخصيين - AI Agents)، (المعالجة المحلية)، و(الخصوصية السيادية). "
            "في كل تغريدة ركز على: (الكيفية)، (التطبيق)، (الفائدة)، و(المقارنة). "
            "ابحث عن الزاوية التي تثير الجدل والضجة الإيجابية. "
            "ضع المصطلحات والأسماء بين أقواس ( ). لا تستخدم هاشتاقات. امنع الهلوسة."
        )

        prompts = {
            "POST": f"حلل هذا الخبر للفرد. ركز على الجدل المثار، الكيفية، التطبيق، والمقارنة: {content}",
            "REPLY": f"رد باحترافية خليجية تثير الجدل الذكي وتجذب المتابعين للنقاش حول تمكين الفرد: {content}",
            "QUIZ": "ابتكر مسابقة تقنية (سؤال وجواب) للفرد عن بناء الوكلاء أو أمن البيانات المحلية بأسلوب نخبوي.",
            "POLL": "ابتكر استطلاع رأي (Poll) يثير ضجة حول موضوع جدلي: هل نثق بـ (الوكلاء) في إدارة أموالنا أم نتمسك بالتحكم اليدوي؟"
        }

        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompts[mode]}],
                timeout=45  # تجنب التعليق الأبدي
            )
            text = f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"
            logger.info(f"تم توليد نص لـ {mode}: {text[:60]}...")
            return text
        except Exception as e:
            logger.error(f"خطأ في _brain لـ {mode}: {e}")
            return ""

    def fetch(self):
        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:5]:
                    title = e.title.strip()
                    # فلترة استبعادية للمؤسسات
                    blacklist = ["stock", "revenue", "quarterly", "acquisition", "ceo", "lawsuit", "hiring", "shares"]
                    if any(x in title.lower() for x in blacklist):
                        continue

                    # استهداف مواضيع الساعة الجدلية مع وزن score
                    targets = {"agent": 1.8, "local llm": 1.6, "privacy": 2.0, "npu": 1.2, "future": 1.0, "autonomous": 1.5, "spatial": 1.1, "personal ai": 1.7}
                    score = 5.0
                    for k, v in targets.items():
                        if k in title.lower():
                            score *= v
                            break

                    h = hashlib.sha256(title.encode()).hexdigest()
                    emb = self._embedding(title)
                    if self._is_semantic_duplicate(emb):
                        continue

                    with sqlite3.connect(CONFIG["DB"]) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title, score, created_at) VALUES (?,?,?,?)",
                                  (h, title, score, datetime.now().isoformat()))
                        c.execute("INSERT OR IGNORE INTO memory (h, embedding) VALUES (?,?)",
                                  (h, json.dumps(emb.tolist())))
                        c.commit()
                logger.info(f"تم جلب عناصر من {src}")
            except Exception as e:
                logger.warning(f"فشل في جلب من {src}: {e}")

    def handle_interactions(self):
        if not self.bot_id:
            return
        try:
            mentions = []
            for mention in tweepy.Paginator(
                self.x.get_users_mentions,
                id=self.bot_id,
                max_results=100
            ).flatten(limit=CONFIG["MAX_REPLIES"] * 2):
                mentions.append(mention)

            with sqlite3.connect(CONFIG["DB"]) as c:
                for m in mentions:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (m.id,)).fetchone():
                        continue
                    reply_text = self._brain(m.text, mode="REPLY")
                    if not reply_text:
                        continue
                    try:
                        self.x.create_tweet(text=reply_text, in_reply_to_tweet_id=m.id)
                        c.execute("INSERT INTO replies VALUES (?,?,?)", (m.id, m.author_id, datetime.now().isoformat()))
                        c.commit()
                        time.sleep(random.uniform(CONFIG["REPLY_DELAY_MIN"], CONFIG["REPLY_DELAY_MAX"]))  # تأخير بشري
                    except tweepy.TooManyRequests as e:
                        self._handle_rate_limit(e)
                    except Exception as e:
                        logger.error(f"فشل في الرد على {m.id}: {e}")
            logger.info(f"تم التعامل مع {len(mentions)} mentions")
        except Exception as e:
            logger.error(f"خطأ في handle_interactions: {e}")

    def _handle_rate_limit(self, e):
        try:
            reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 900))
            wait_sec = reset_time - time.time() + random.randint(10, 60)
            logger.warning(f"Rate limit → نوم {wait_sec // 60:.1f} دقيقة")
            time.sleep(max(wait_sec, 300))
        except Exception as inner_e:
            logger.error(f"خطأ في معالجة rate limit: {inner_e}")
            time.sleep(300)

    def dispatch(self):
        now = datetime.now()
        if now.hour not in CONFIG["PEAK_HOURS"]:
            return

        with sqlite3.connect(CONFIG["DB"]) as c:
            last = c.execute("SELECT value FROM meta WHERE key='last_publish'").fetchone()
            if last and (now - datetime.fromisoformat(last[0])).total_seconds() / 60 < CONFIG["COOLDOWN_MINUTES"]:
                return

            # تحقق الحد اليومي
            today = now.date().isoformat()
            daily_last = c.execute("SELECT value FROM meta WHERE key='daily_tweet_count'").fetchone()
            if daily_last and daily_last[0].startswith(today):
                self.daily_tweet_count = int(daily_last[0].split('|')[1])
            else:
                self.daily_tweet_count = 0

            if self.daily_tweet_count >= CONFIG["DAILY_MAX_TWEETS"]:
                logger.warning("وصلنا الحد اليومي للتغريدات")
                return

            rand = random.random()
            try:
                if rand < CONFIG["QUIZ_CHANCE"]:
                    text = self._brain("", mode="QUIZ")
                    if text:
                        self.x.create_tweet(text=text)
                        self._update_tweet_count(c, now)

                elif rand < (CONFIG["QUIZ_CHANCE"] + CONFIG["POLL_CHANCE"]):
                    raw = self._brain("", mode="POLL")
                    poll_text = raw[:200].rsplit(' ', 1)[0] if len(raw) > 200 else raw  # تقصير آمن
                    options = self._safe_poll_options(raw)
                    try:
                        self.x.create_tweet(
                            text=poll_text,
                            poll_options=options,
                            poll_duration_minutes=1440
                        )
                        self._update_tweet_count(c, now)
                    except tweepy.TweepyException as e:
                        logger.warning(f"فشل الاستطلاع: {e} → fallback إلى تغريدة نصية")
                        self.x.create_tweet(text=raw[:280])
                        self._update_tweet_count(c, now)

                else:
                    row = c.execute("SELECT id, title FROM queue WHERE status='PENDING' ORDER BY score DESC LIMIT 1").fetchone()
                    if row:
                        content = self._brain(row[1], mode="POST")
                        if content:
                            self.x.create_tweet(text=content)
                            c.execute("UPDATE queue SET status='PUBLISHED' WHERE id=?", (row[0],))
                            self._update_tweet_count(c, now)

                c.execute("REPLACE INTO meta VALUES ('last_publish',?)", (now.isoformat(),))
                c.commit()
            except tweepy.TooManyRequests as e:
                self._handle_rate_limit(e)
            except Exception as e:
                logger.error(f"خطأ في dispatch: {e}")

    def _update_tweet_count(self, c, now):
        self.daily_tweet_count += 1
        today = now.date().isoformat()
        c.execute("REPLACE INTO meta VALUES ('daily_tweet_count',?)", (f"{today}|{self.daily_tweet_count}",))

    def _safe_poll_options(self, text):
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        options = [l[:25] for l in lines if 1 <= len(l) <= 25][:4]  # قيود X: 2–4 خيارات، max 25 حرف
        if len(options) < 2:
            options = ["ثقة كاملة", "حذر شديد", "رفض قاطع", "أحتاج تجربة"]
        return options

    def run_forever(self):
        while True:
            try:
                self.fetch()
                self.handle_interactions()
                self.dispatch()
                sleep_time = random.randint(600, 1500)  # 10–25 دقيقة
                logger.info(f"نوم لـ {sleep_time // 60} دقيقة")
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                logger.info("إيقاف يدوي")
                break
            except Exception as e:
                logger.critical(f"انهيار كبير: {e}", exc_info=True)
                time.sleep(300)  # 5 دقائق ثم إعادة

if __name__ == "__main__":
    bot = SovereignControversyV550()
    bot.run_forever()
