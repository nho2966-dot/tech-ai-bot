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

# 1. الإعدادات واللوج
load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("sovereign_final.log"), logging.StreamHandler()]
)
logger = logging.getLogger("SovereignAI")

# 2. محرك الذكاء الاصطناعي - إصلاح معامل creative
class SovereignAI:
    def __init__(self, api_key):
        if not api_key: raise ValueError("GEMINI_KEY is missing!")
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash" 
        self.sys_prompt = (
            "أنت خبير سيادي متخصص في الذكاء الاصطناعي (Artificial Intelligence and its latest tools) والأمن السيبراني. "
            "مهمتك: تحليل الأدوات الجديدة، وتوعية الأفراد بمخاطر الهندسة الاجتماعية (Social Engineering). "
            "الأسلوب: خليجي وقور، مهني، مباشر. التركيز على التمكين والحماية."
        )

    def generate(self, prompt, max_chars=280, creative=False):
        try:
            # استخدام creative لضبط الحرارة (Temperature)
            temp = 0.7 if creative else 0.4
            config = types.GenerateContentConfig(
                temperature=temp,
                system_instruction=self.sys_prompt,
                max_output_tokens=500
            )
            response = self.client.models.generate_content(
                model=self.model_id, contents=prompt, config=config
            )
            # بصمة لمنع تكرار المحتوى رقمياً
            fingerprint = "\n\u200c" + "".join(random.choices(["\u200b", "\u200d"], k=2))
            return (response.text.strip() + fingerprint)[:max_chars]
        except Exception as e:
            logger.error(f"AI Generation Error: {e}")
            return None

# 3. إدارة الذاكرة
class BotMemory:
    def __init__(self, db_path="data/sovereign_cyber.db"):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._setup()

    def _setup(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS interactions (id TEXT PRIMARY KEY, ts TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()

    def is_new(self, content):
        h = hashlib.md5(content.strip().encode()).hexdigest()
        self.cursor.execute("SELECT 1 FROM history WHERE hash=?", (h,))
        if self.cursor.fetchone(): return False
        self.cursor.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now().isoformat()))
        self.conn.commit()
        return True

# 4. المنظومة المتكاملة
class SovereignBot:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
        self.ai = SovereignAI(api_key)
        self.memory = BotMemory()
        
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.acc_id = str(os.getenv("X_ACCOUNT_ID"))
        self.manual_mode = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    def fetch_verified_data(self):
        sources = [
            "https://thehackernews.com/feeds/posts/default",
            "https://openai.com/news/rss.xml",
            "https://krebsonsecurity.com/feed/",
            "https://deepmind.google/blog/rss.xml"
        ]
        pool = []
        for url in sources:
            try:
                f = feedparser.parse(url)
                for entry in f.entries[:3]:
                    pool.append({"title": entry.title, "link": entry.link})
            except: continue
        return pool

    def execute_mission(self, force=False):
        if not force:
            if datetime.now().hour not in [9, 13, 17, 21]: return

        news = self.fetch_verified_data()
        if not news: return
        item = random.choice(news)
        
        # تحليل استراتيجي (الخبر الأساسي)
        prompt = f"حلل الخبر: {item['title']}. الرابط: {item['link']}. ركز على التمكين التقني والحذر من الهندسة الاجتماعية."
        content = self.ai.generate(prompt, creative=True)

        if content and self.memory.is_new(content):
            try:
                main = self.x.create_tweet(text=content)
                main_id = main.data['id']
                logger.info(f"🚀 Mission success: {main_id}")

                # ثريد نصيحة أمنية
                time.sleep(20)
                tip = self.ai.generate(f"أعط نصيحة أمنية عملية بناءً على: {item['title']}")
                self.x.create_tweet(text=tip, in_reply_to_tweet_id=main_id)

                # استطلاع رأي
                time.sleep(15)
                self.x.create_tweet(
                    text="هل تعتقد أن أدوات الذكاء الاصطناعي الحالية تزيد من سهولة وقوع الأفراد في فخ الهندسة الاجتماعية؟",
                    poll_options=["نعم، الخطر تضاعف", "لا، الوعي زاد أيضاً", "تعتمد على وعي الفرد"],
                    poll_duration_minutes=1440,
                    in_reply_to_tweet_id=main_id
                )
            except Exception as e:
                logger.error(f"Execution Error: {e}")

    def run(self):
        # هنا يمكن إضافة دالة smart_replies إذا رغبت
        self.execute_mission(force=self.manual_mode)

if __name__ == "__main__":
    SovereignBot().run()
