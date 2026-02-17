import os
import sqlite3
import logging
import time
import random
import hashlib
import requests
import tweepy
import feedparser
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime, timezone
from google import genai

# إعداد السجلات لمتابعة الأداء
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignExpert:
    def __init__(self):
        # ربط المفاتيح السرية
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "x_api": os.getenv("X_API_KEY"),
            "x_secret": os.getenv("X_API_SECRET"),
            "x_token": os.getenv("X_ACCESS_TOKEN"),
            "x_token_secret": os.getenv("X_ACCESS_SECRET")
        }
        self.db_path = "data/expert_v26.db"
        self._setup_brains()
        self._setup_x()
        self._init_db()

    def _setup_brains(self):
        self.brain = genai.Client(api_key=self.keys["gemini"])

    def _setup_x(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=self.keys["x_api"], consumer_secret=self.keys["x_secret"],
                access_token=self.keys["x_token"], access_token_secret=self.keys["x_token_secret"]
            )
            auth = tweepy.OAuth1UserHandler(self.keys["x_api"], self.keys["x_secret"], self.keys["x_token"], self.keys["x_token_secret"])
            self.api_v1 = tweepy.API(auth)
            logging.info("✅ أنظمة الخبير متصلة وجاهزة..")
        except Exception as e: 
            logging.error(f"❌ خطأ في ربط X: {e}")

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS waiting_room (hash TEXT PRIMARY KEY, content TEXT, url TEXT, ts DATETIME)")

    def _get_image(self, url):
        try:
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            img = soup.find("meta", property="og:image")
            return img["content"] if img else None
        except: return None

    def fetch_exclusive_news(self):
        logging.info("🌐 جاري البحث عن أخبار تقنية جديدة...")
        feeds = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
        ]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # سحب آخر 5 أخبار
                h = hashlib.md5(entry.link.encode()).hexdigest()
                with sqlite3.connect(self.db_path) as conn:
                    # نتحقق إذا الخبر قديم أو تم نشره سابقاً
                    if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                        conn.execute("INSERT OR REPLACE INTO waiting_room VALUES (?, ?, ?, ?)",
                                    (h, entry.title, entry.link, datetime.now(timezone.utc)))
        logging.info("✅ تم تحديث قائمة الأخبار بنجاح.")

    def handle_posting(self):
        """نظام النشر القسري لضمان ظهور التغريدة الآن"""
        self.fetch_exclusive_news() # جلب الأخبار أولاً
        
        with sqlite3.connect(self.db_path) as conn:
            # نسحب أول خبر متوفر في غرفة الانتظار فوراً
            target = conn.execute("SELECT hash, content, url FROM waiting_room LIMIT 1").fetchone()
            
            if target:
                logging.info(f"🎯 تم العثور على محتوى: {target[1]}. جاري النشر...")
                self._publish_as_human(*target)
            else:
                logging.warning("⚠️ لا توجد أخبار جديدة في هذه اللحظة.")

    def _publish_as_human(self, h, content, url):
        try:
            # صياغة بشرية خليجية متمكنة
            prompt = f"""
            بصفتك خبير تقني خليجي متمكن، اكتب تغريدة عن هذا الخبر بأسلوبك الشخصي (لهجة بيضاء مهنية).
            - اجعلها مشوقة وتركز على أدوات الذكاء الاصطناعي وأثرها على الأفراد.
            - استخدم إيموجي واحد مناسب.
            - لا تذكر أنك ذكاء اصطناعي.
            - اختم بكلمة 'المصدر:' ثم الرابط.
            الخبر: {content}
            الرابط: {url}
            """
            response = self.brain.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            txt = response.text.strip()
            
            img_url = self._get_image(url)
            m_ids = None
            if img_url:
                img_data = requests.get(img_url).content
                with BytesIO(img_data) as f:
                    m = self.api_v1.media_upload(filename="news_img.jpg", file=f)
                    m_ids = [m.media_id]

            self.x_client.create_tweet(text=txt[:280], media_ids=m_ids)
            
            # تحديث الذاكرة لمنع التكرار
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                conn.commit()
            logging.info("🚀 مبروك! التغريدة الآن لايف على حسابك.")
        except Exception as e: 
            logging.error(f"❌ فشل النشر النهائي: {e}")

    def handle_radar(self):
        # رادار التفاعل لجذب المتابعين
        TARGETS = ["7alsabe", "faisalsview", "elonmusk", "OpenAI"]
        for target in TARGETS:
            try:
                user = self.x_client.get_user(username=target).data
                tweets = self.x_client.get_users_tweets(id=user.id, max_results=5).data
                if not tweets: continue
                
                for tweet in tweets:
                    h = hashlib.md5(f"reply_{tweet.id}".encode()).hexdigest()
                    with sqlite3.connect(self.db_path) as conn:
                        if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): continue
                    
                    if any(word in tweet.text.lower() for word in ["ai", "ذكاء", "tech", "تطبيق"]):
                        self._smart_engage(tweet, target, h)
                        break
            except: continue

    def _smart_engage(self, tweet, username, h):
        prompt = f"رد كخبير تقني خليجي بذكاء على تغريدة {username} حول التقنية. اجعل الرد بشرياً جداً ومثيراً للاهتمام. التغريدة: {tweet.text}"
        res = self.brain.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        reply = res.text.strip()
        self.x_client.create_tweet(text=reply[:275], in_reply_to_tweet_id=tweet.id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
            conn.commit()
        logging.info(f"💬 تم الرد بنجاح على {username}")

if __name__ == "__main__":
    expert = SovereignExpert()
    expert.handle_posting() # النشر الفوري
    expert.handle_radar()   # التفاعل مع المؤثرين
