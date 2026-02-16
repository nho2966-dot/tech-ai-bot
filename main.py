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

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("sovereign.log"), logging.StreamHandler()]
)
logger = logging.getLogger("SovereignAI")

# 2. محرك الذكاء الاصطناعي - إصلاح الخطأ التقني
class SovereignAI:
    def __init__(self, api_key):
        if not api_key: raise ValueError("Missing GEMINI_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash" 
        self.sys_prompt = (
            "أنت مستشار سيادي خبير في الذكاء الاصطناعي (Artificial Intelligence and its latest tools) والأمن السيبراني. "
            "مهمتك: تحليل التقنيات الجديدة وتوعية الأفراد بمخاطر الهندسة الاجتماعية (Social Engineering). "
            "أسلوبك: خليجي وقور، رصين، مباشر، ومهني جداً."
        )

    # إضافة **kwargs لضمان عدم حدوث خطأ TypeError مستقبلاً
    def generate(self, prompt, max_chars=280, creative=False, **kwargs):
        try:
            temp = 0.7 if creative else 0.3
            config = types.GenerateContentConfig(
                temperature=temp,
                system_instruction=self.sys_prompt,
                max_output_tokens=500
            )
            response = self.client.models.generate_content(
                model=self.model_id, contents=prompt, config=config
            )
            # بصمة رقمية لمنع التكرار
            fingerprint = "\n\u200c" + "".join(random.choices(["\u200b", "\u200d"], k=2))
            return (response.text.strip() + fingerprint)[:max_chars]
        except Exception as e:
            logger.error(f"AI Generation Error: {e}")
            return None

# 3. إدارة الذاكرة وقاعدة البيانات
class BotMemory:
    def __init__(self, db_path="data/sovereign.db"):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._setup()

    def _setup(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS interactions (id TEXT PRIMARY KEY, ts TEXT)")
        self.conn.commit()

    def is_unique(self, content):
        h = hashlib.md5(content.strip().encode()).hexdigest()
        self.cursor.execute("SELECT 1 FROM history WHERE hash=?", (h,))
        if self.cursor.fetchone(): return False
        self.cursor.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now().isoformat()))
        self.conn.commit()
        return True

# 4. المنظومة التشغيلية
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
        self.manual_run = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

    def fetch_data(self):
        """جلب بيانات من مصادر موثوقة (AI + CyberSecurity)"""
        feeds = [
            "https://thehackernews.com/feeds/posts/default",
            "https://openai.com/news/rss.xml",
            "https://krebsonsecurity.com/feed/"
        ]
        results = []
        for url in feeds:
            try:
                f = feedparser.parse(url)
                for entry in f.entries[:3]:
                    results.append({"title": entry.title, "link": entry.link})
            except: continue
        return results

    def execute_post(self, force=False):
        if not force:
            if datetime.now().hour not in [9, 13, 17, 21]: return

        news = self.fetch_data()
        if not news: return
        item = random.choice(news)
        
        # التغريدة الأولى: تحليل الخبر
        p1 = f"حلل استراتيجياً: {item['title']}. الرابط: {item['link']}. ركز على التمكين التقني والحماية."
        text1 = self.ai.generate(p1, creative=True)

        if text1 and self.memory.is_unique(text1):
            try:
                main = self.x.create_tweet(text=text1)
                mid = main.data['id']
                logger.info(f"🚀 Published Tweet: {mid}")

                # التغريدة الثانية: نصيحة أمنية (Thread)
                time.sleep(15)
                p2 = f"بناءً على {item['title']}، قدم نصيحة أمنية عملية للوقاية من الهندسة الاجتماعية."
                text2 = self.ai.generate(p2)
                self.x.create_tweet(text=text2, in_reply_to_tweet_id=mid)

                # التغريدة الثالثة: استطلاع رأي
                time.sleep(10)
                self.x.create_tweet(
                    text="هل تعتقد أن الذكاء الاصطناعي سيجعل اكتشاف محاولات الاختراق أصعب على الفرد العادي؟",
                    poll_options=["نعم، الخطر في ازدياد", "لا، الوعي كفيل بالحماية", "الأدوات الأمنية ستتطور"],
                    poll_duration_minutes=1440,
                    in_reply_to_tweet_id=mid
                )
            except Exception as e:
                logger.error(f"X Post Error: {e}")

    def run(self):
        # تنفيذ النشر
        self.execute_post(force=self.manual_run)

if __name__ == "__main__":
    SovereignBot().run()
