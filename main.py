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

# 2. محرك الذكاء الاصطناعي (Gemini 2.0) - التركيز على القيمة العملية للأدوات
class SovereignAI:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash" 
        self.sys_prompt = (
            "أنت مستشار استراتيجي في الذكاء الاصطناعي وأحدث أدواته. "
            "أسلوبك: احترافي جداً، رصين، مباشر، وخليجي بيضاء وقورة. "
            "المهمة: تحليل أدوات AI الجديدة فور صدورها وشرح (كيفية الاستخدام) و(الفائدة العملية الملموسة) للمتابع. "
            "تجنب الرموز الكثيرة والحشو الإنشائي. ركز على التمكين الرقمي للفرد."
        )

    def generate(self, prompt, max_chars=280, creative=False):
        try:
            config = types.GenerateContentConfig(
                temperature=0.3 if not creative else 0.7,
                system_instruction=self.sys_prompt,
                max_output_tokens=400
            )
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=config
            )
            # بصمة رقمية مشفرة (Invisible Fingerprint) لمنع الحظر
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

# 4. المنظومة التشغيلية (X API + News Scraper)
class SovereignBot:
    def __init__(self):
        self.ai = SovereignAI(os.getenv("GEMINI_API_KEY"))
        self.memory = BotMemory()
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
        # مصادر عالمية مخصصة لأحدث أدوات AI
        feeds = [
            "https://www.futuretools.io/rss",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
            "https://techcrunch.com/category/artificial-intelligence/feed/"
        ]
        news = []
        for url in feeds:
            try:
                f = feedparser.parse(url)
                for entry in f.entries[:5]:
                    news.append({"title": entry.title, "link": entry.link})
            except: continue
        return news

    def is_peak_hour(self):
        # ذروة التفاعل في الخليج (صباحاً، ظهراً، ومساءً)
        hour = datetime.now().hour
        return hour in [8, 9, 10, 13, 14, 15, 20, 21, 22, 23]

    def post_strategic_content(self):
        """نشر السبق التقني بأسلوب القيمة العملية"""
        news = self.fetch_ai_scoops()
        if not news: return
        
        random.shuffle(news)
        selected = news[0]
        
        # صياغة تركز على الفائدة المباشرة
        prompt = (
            f"حلل هذه الأداة/الخبر برؤية عملية: {selected['title']}. "
            f"الرابط: {selected['link']}. "
            "اشرح للمتابع كيف يستفيد منها الآن لرفع إنتاجيته أو تطوير عمله."
        )
        main_text = self.ai.generate(prompt, creative=True)
        
        if main_text and not self.memory.is_duplicate(main_text):
            try:
                resp = self.x.create_tweet(text=main_text)
                main_id = resp.data['id']
                logger.info(f"🚀 Published AI Scoop: {main_id}")

                # Thread تحليلي (نقطة واحدة عميقة)
                time.sleep(20)
                thread_prompt = f"أعطِ نصيحة احترافية واحدة لم تذكر سابقاً حول كيفية دمج هذه التقنية في سير العمل اليومي: {selected['title']}"
                thread_text = self.ai.generate(thread_prompt)
                thread_resp = self.x.create_tweet(text=thread_text, in_reply_to_tweet_id=main_id)

                # استطلاع رأي (Poll) قيادي
                self.x.create_tweet(
                    text="في ظل تسارع أدوات AI، هل تعتقد أن المهارة الأهم حالياً هي (صياغة الأوامر - Prompt Engineering) أم (التحليل الاستراتيجي)؟",
                    poll_options=["صياغة الأوامر", "التحليل الاستراتيجي", "كلاهما معاً", "مهارات أخرى"],
                    poll_duration_minutes=1440,
                    in_reply_to_tweet_id=thread_resp.data['id']
                )
            except Exception as e:
                logger.error(f"X Post Error: {e}")

    def smart_replies(self):
        """الردود الذكية الصارمة - تعزيز الهوية الاستشارية"""
        last_id = self.memory.get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.acc_id, since_id=last_id)
            if not mentions.data: return

            for tweet in reversed(mentions.data):
                if self.memory.is_duplicate(f"reply_{tweet.id}") or str(tweet.author_id) == str(self.acc_id):
                    continue 

                ai_keywords = ["ذكاء", "ai", "أداة", "بوت", "نموذج", "كيف", "تطوير"]
                if any(k in tweet.text.lower() for k in ai_keywords):
                    reply = self.ai.generate(f"رد بوقار استشاري على هذا الاستفسار التقني: {tweet.text}", max_chars=220)
                    self.x.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    logger.info(f"💬 Strategic Reply sent to {tweet.id}")
                    time.sleep(25)
            
            self.memory.set_meta("last_mention_id", mentions.data[0].id)
        except Exception as e:
            logger.error(f"Replies Error: {e}")

    def run(self):
        logger.info("🛡️ Sovereign AI System v4.0 Active")
        self.smart_replies()
        
        if self.is_peak_hour():
            last_hour = self.memory.get_meta("last_post_hour", "-1")
            if last_hour != str(datetime.now().hour):
                self.post_strategic_content()
                self.memory.set_meta("last_post_hour", str(datetime.now().hour))
        
        logger.info("🏁 Cycle Completed Successfully.")

if __name__ == "__main__":
    SovereignBot().run()
