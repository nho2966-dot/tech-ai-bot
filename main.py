import os
import sqlite3
import logging
import hashlib
import random
import re
import time
from datetime import datetime, timezone

import tweepy
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

# 1. الإعدادات العامة
load_dotenv()
DB_FILE = "news.db"

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, replied_at TEXT)")
        conn.commit()
        conn.close()

    def _init_clients(self):
        # Gemini & AI Clients
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"), http_options={'api_version': 'v1'})
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        # X Client
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # --- [2. أنظمة التحليل الذكية] ---

    def calculate_credibility(self, source_name, entry):
        """تقييم المصداقية: مصدر (40%) + محتوى (40%) + حداثة (20%)"""
        score = 50
        authority = {"The Verge": 35, "9to5Mac": 30, "MacRumors": 30, "Bloomberg": 40, "Reuters": 40}
        score += authority.get(source_name, 15)

        content = (entry.title + " " + entry.description).lower()
        if any(w in content for w in ["official", "confirmed", "announces", "رسمياً"]): score += 20
        if any(w in content for w in ["leak", "rumor", "تسريب", "إشاعة"]): score -= 25

        try:
            pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            hours_old = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
            if hours_old < 6: score += 10
            elif hours_old > 24: score -= 15
        except: pass
        return round(max(1, min(100, score)) / 10, 1)

    def extract_dynamic_tags(self, title):
        """توليد وسوم بناءً على الكلمات المفتاحية في العنوان"""
        keywords = {
            "apple": "#آبل #Apple", "iphone": "#آيفون", "nvidia": "#انفيديا #Nvidia",
            "ai": "#الذكاء_الاصطناعي #AI", "tesla": "#تسلا", "leak": "#تسريبات",
            "samsung": "#سامسونج", "meta": "#ميتا", "waymo": "#Waymo"
        }
        tags = set(["#تقنية", "#سبق_تقني"])
        for key, val in keywords.items():
            if key in title.lower():
                tags.add(val)
        return " ".join(tags)

    # --- [3. أنظمة النشر الآمنة] ---

    def safe_post(self, text, reply_id=None):
        """إعادة محاولة النشر تلقائياً في حال فشل الـ API"""
        for i in range(3):
            try:
                res = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=reply_id)
                return res.data['id']
            except Exception as e:
                logging.warning(f"⚠️ محاولة {i+1} فشلت: {e}")
                time.sleep(10 * (i + 1))
        return None

    def ai_ask(self, system_prompt, user_content):
        try:
            res = self.gemini_client.models.generate_content(model='gemini-1.5-flash', contents=f"{system_prompt}\n\n{user_content}")
            return res.text.strip()
        except:
            try:
                res = self.ai_qwen.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}])
                return res.choices[0].message.content.strip()
            except: return None

    def post_thread(self, content, title):
        """تقسيم احترافي مع وسوم ديناميكية وقص ذكي"""
        raw_parts = re.split(r'\n\s*\d+[\/\.\)]\s*|\n\n', content.strip())
        tweets = [t.strip() for t in raw_parts if len(t.strip()) > 10]
        tags = self.extract_dynamic_tags(title)
        
        last_id = None
        for i, tweet in enumerate(tweets[:5]):
            text = f"{i+1}/ {tweet}"
            if i == len(tweets[:5]) - 1: text += f"\n\n{tags}"
            if len(text) > 280: text = text[:277].rsplit(' ', 1)[0] + "..."
            
            last_id = self.safe_post(text, last_id)
            if not last_id: break
        return True

    def run_cycle(self):
        sources = [
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"},
            {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"}
        ]
        targets = ["apple", "nvidia", "leak", "rumor", "ai", "tesla", "عاجل", "تسريب"]
        
        random.shuffle(sources)
        for src in sources:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:10]:
                # فلتر الـ 36 ساعة
                try:
                    pub_time = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - pub_time).total_seconds() > 129600: continue
                except: continue

                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    if any(w in e.title.lower() for w in targets):
                        score = self.calculate_credibility(src['name'], e)
                        sys_prompt = f"أنت محرر تقني سعودي نخبوي. ابدأ بـ '📊 تقييم المصداقية: {score}/10'. صغ الخبر كثريد فخم ومركز."
                        content = self.ai_ask(sys_prompt, f"{e.title}\n{e.description}")
                        
                        if content and "أ" in content:
                            if self.post_thread(content, e.title):
                                conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                                conn.commit()
                                conn.close()
                                return
                conn.close()

if __name__ == "__main__":
    TechEliteBot().run_cycle()
