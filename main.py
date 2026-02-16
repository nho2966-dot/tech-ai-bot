import os
import time
import random
import hashlib
import sqlite3
import logging
import feedparser
import tweepy
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. إعدادات النظام واللوج (Logging)
load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("ai_sovereign.log"), logging.StreamHandler()]
)
logger = logging.getLogger("SovereignBot")

# 2. محرك الذكاء الاصطناعي (Gemini 2.0)
class SovereignAI:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Missing Gemini API Key!")
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash" 
        self.sys_prompt = (
            "أنت مستشار استراتيجي في الذكاء الاصطناعي وأحدث أدواته. "
            "أسلوبك: احترافي جداً، رصين، مباشر، وخليجي بيضاء وقورة. "
            "المهمة: تحليل أدوات AI الجديدة فور صدورها وشرح قيمتها الملموسة. "
            "تجنب الرموز الكثيرة والحشو الإنشائي."
        )

    def generate(self, prompt, max_chars=280, creative=False):
        try:
            config = types.GenerateContentConfig(
                temperature=0.3 if not creative else 0.7,
                system_instruction=self.sys_prompt,
                max_output_tokens=400
            )
            response = self.client.models.generate_content(
                model=self.model_id, contents=prompt, config=config
            )
            safe_suffix = "\n\u200b" + "".join(random.choices(["\u200c", "\u200b"], k=3))
            return (response.text.strip() + safe_suffix)[:max_chars]
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return None

# 3. إدارة الذاكرة الصارمة (SQLite)
class BotMemory:
    def __init__(self, db_path="data/sovereign_ai.db"):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._setup()

    def _setup(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, type TEXT, ts TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()

    def is_duplicate(self, content):
        h = hashlib.md5(content.strip().encode()).hexdigest()
        self.cursor.execute("SELECT 1 FROM history WHERE hash=?", (h,))
        if self.cursor.fetchone(): return True
        self.cursor.execute("INSERT INTO history VALUES (?, 'POST', ?)", (h, datetime.now().isoformat()))
        self.conn.commit()
        return False

    def get_meta(self, key, default="0"):
        self.cursor.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = self.cursor.fetchone()
        return row[0] if row else default

    def set_meta(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, str(value)))
        self.conn.commit()

# 4. المنظومة التشغيلية
class SovereignBot:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
        self.ai = SovereignAI(api_key)
        self.memory = BotMemory()
        
        # تم إغلاق القوس بشكل صحيح هنا
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.acc_id = os.getenv("X_ACCOUNT_ID")

    def fetch_ai_scoops(self):
        feeds = [
            "https://www.futuretools.io/rss",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
        ]
        news = []
        for url in feeds:
            try:
                f = feedparser.parse(url)
                for entry in f.entries[:5]:
                    news.append({"title": entry.title, "link": entry.link})
            except: continue
        return news

    def post_strategic_content(self):
        news = self.fetch_ai_scoops()
        if not news: return
        selected = random.choice(news)
        
        prompt = f"حلل أداة AI هذه برؤية عملية: {selected['title']}. الرابط: {selected['link']}"
        main_text = self.ai.generate(prompt, creative=True)
        
        if main_text and not self.memory.is_duplicate(main_text):
            try:
                self.x.create_tweet(text=main_text)
                logger.info("🚀 Tweet Published Successfully")
            except Exception as e:
                logger.error(f"X Post Error: {e}")

    def run(self):
        # تشغيل المنطق الأساسي
        self.post_strategic_content()

if __name__ == "__main__":
    SovereignBot().run()
