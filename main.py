import os
import sqlite3
import feedparser
import tweepy
import time
import hashlib
import sys
from datetime import datetime, timezone
from google import genai

# === إعدادات المصادر والكلمات المفتاحية ===
TECH_SOURCES = {
    "global": {
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "TechCrunch": "http://feeds.feedburner.com/TechCrunch/",
        "Wired": "https://www.wired.com/feed/category/gear/latest/rss",
        "MIT Technology Review": "https://www.technologyreview.com/feed/"
    },
    "arabic": {
        "عالم التقنية": "https://www.tech-wd.com/wd-rss-feed.xml",
        "البوابة العربية للأخبار التقنية": "https://www.aitnews.com/feed/",
        "أراجيك تك": "https://www.arageek.com/feed/tech"
    }
}

KEYWORDS = {
    "ذكاء اصطناعي": ["AI", "Artificial Intelligence", "ذكاء اصطناعي", "Machine Learning", "Deep Learning", "Generative AI"],
    "أجهزة حديثة": ["Smartphone", "IoT", "Pixel", "MacBook", "iPhone", "Laptop"],
    "أمن سيبراني": ["Cybersecurity", "أمن سيبراني", "Hacking", "Ransomware"],
    "عام": ["تكنولوجيا", "ابتكار", "Technology", "Innovation"]
}

class SovereignBot:
    def __init__(self):
        # ربط العقل (Gemini)
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        
        # ربط المنصة (X)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        self.db_path = "data/sovereign_v8.db"
        self._init_db()
        
        # التعليمات السيادية
        self.sys_instruction = (
            "Focus on Artificial Intelligence and its latest tools for individuals. "
            "Use Gulf dialect (خليجي أبيض). Professional and accurate. "
            "NEVER mention 'Industrial Revolution', replace it with 'Artificial Intelligence and its latest tools'. "
            "No symbols, no Chinese characters. Focus on individuals, not companies."
        )

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, type TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS coin (tool TEXT, info TEXT)")

    def _is_seen(self, h):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone() is not None

    def _mark_done(self, h, t_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (hash, type) VALUES (?, ?)", (h, t_type))
            conn.commit()

    def _ask_ai(self, prompt):
        try:
            res = self.ai_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return res.text.strip()
        except Exception as e:
            print(f"⚠️ AI Error: {e}")
            return None

    def classify_topic(self, content):
        content_lower = content.lower()
        for topic, keywords in KEYWORDS.items():
            if any(k.lower() in content_lower for k in keywords):
                return topic
        return "عام"

    # --- المستوى 1: أخبار جوجل الرسمية ---
    def level_1_google(self):
        print("🔍 فحص أخبار جوجل...")
        feed = feedparser.parse("https://blog.google/products/gemini/rss/")
        for entry in feed.entries[:2]:
            h = hashlib.md5((entry.title + entry.link).encode()).hexdigest()
            if not self._is_seen(h):
                summary = self._ask_ai(f"لخص هذا السكوب الرسمي من جوجل بلهجة خليجية للفرد:\n{entry.title} - {entry.link}")
                topic = self.classify_topic(summary or entry.title)
                if self._post(summary, h, f"google_{topic}", "Google"):
                    return True
        return False

    # --- المستوى 2: جوك (RSS العالمية والعربية) ---
    def level_2_jok(self):
        print("🔍 فحص مصادر جوك...")
        now = datetime.now(timezone.utc)
        for cat, sources in TECH_SOURCES.items():
            for name, url in sources.items():
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    h = hashlib.md5((entry.title + entry.link).encode()).hexdigest()
                    if not self._is_seen(h):
                        # تصفية المحتوى حسب الكلمات المفتاحية
                        content_check = entry.title + " " + entry.get("summary", "")
                        if any(k.lower() in content_check.lower() for kws in KEYWORDS.values() for k in kws):
                            summary = self._ask_ai(f"لخص هذا الخبر بلهجة خليجية (سكوب للفرد):\n{entry.title}\nالرابط: {entry.link}")
                            topic = self.classify_topic(summary or entry.title)
                            if self._post(summary, h, f"jok_{name}_{topic}", name):
                                return True
        return False

    # --- المستوى 3: كوين (الخزين) ---
    def level_3_coin(self):
        print("🔍 فحص الخزين الاستراتيجي...")
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT tool, info FROM coin ORDER BY RANDOM() LIMIT 1").fetchone()
            if res:
                h = hashlib.md5(res[0].encode()).hexdigest()
                if not self._is_seen(h):
                    summary = self._ask_ai(f"اكتب تغريدة إبداعية عن هذه الأداة بلهجة خليجية: {res[0]} - {res[1]}")
                    topic = self.classify_topic(summary or res[0])
                    if self._post(summary, h, f"coin_{topic}", "Coin"):
                        return True
        return False

    def _post(self, text, h, t_type, source):
        if not text: return False
        try:
            # صياغة نهائية احترافية
            final_text = f"{text[:240]}\n\n🔗 المصدر: {source}"
            self.x_client.create_tweet(text=final_text)
            self._mark_done(h, t_type)
            print(f"✅ تم النشر: {t_type} من {source}")
            return True
        except Exception as e:
            if "429" in str(e):
                print("🛑 حظر مؤقت (429). الإغلاق للراحة.")
                sys.exit(0)
            print(f"❌ فشل النشر: {e}")
            return False

if __name__ == "__main__":
    bot = SovereignBot()
    # تنفيذ التسلسل الهرمي (جوجل -> جوك -> كوين)
    if not bot.level_1_google():
        if not bot.level_2_jok():
            bot.level_3_coin()
