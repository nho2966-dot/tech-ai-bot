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
from datetime import datetime, timedelta, timezone
from google import genai

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class SovereignExpert:
    def __init__(self):
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
            logging.info("✅ أنظمة الخبير جاهزة..")
        except Exception as e: logging.error(f"❌ خطأ اتصال: {e}")

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
        # سحب من مصادر متنوعة لتقليل التكرار
        feeds = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
        ]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                h = hashlib.md5(entry.link.encode()).hexdigest()
                with sqlite3.connect(self.db_path) as conn:
                    if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                        conn.execute("INSERT OR REPLACE INTO waiting_room VALUES (?, ?, ?, ?)",
                                    (h, entry.title, entry.link, datetime.now(timezone.utc)))

    def handle_posting(self):
        now = datetime.now(timezone.utc)
        # إضافة عنصر العشوائية في وقت النشر (بين 0 لـ 5 دقائق إضافية)
        random_delay = random.randint(0, 5)
        with sqlite3.connect(self.db_path) as conn:
            target = conn.execute("SELECT hash, content, url FROM waiting_room WHERE ts <= ? LIMIT 1", 
                                 (now - timedelta(minutes=10 + random_delay),)).fetchone()
            if target:
                self._publish_as_human(*target)

    def _publish_as_human(self, h, content, url):
        try:
            # صياغة "بشرية" باحترافية خليجية
            prompt = f"""
            أنت خبير تقني خليجي متمكن. صغ هذا الخبر بأسلوبك الشخصي (لهجة بيضاء مهنية). 
            ركز على الفائدة المباشرة للناس من 'أدوات الذكاء الاصطناعي'. 
            تجنب الأسلوب الروبوتي، استخدم ايموجي واحد أو اثنين بذكاء. 
            اختم بكلمة 'المصدر:' متبوعة بالرابط.
            الخبر: {content} - {url}
            """
            txt = self.brain.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
            
            img_url = self._get_image(url)
            m_ids = None
            if img_url:
                img_data = requests.get(img_url).content
                with BytesIO(img_data) as f:
                    m = self.api_v1.media_upload(filename="post.jpg", file=f)
                    m_ids = [m.media_id]

            self.x_client.create_tweet(text=txt[:278], media_ids=m_ids)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
                conn.execute("DELETE FROM waiting_room WHERE hash=?", (h,))
                conn.commit()
            logging.info("🎯 تم نشر محتوى يجذب العين!")
        except Exception as e: logging.error(f"❌ فشل النشر: {e}")

    def handle_radar(self):
        """نظام الردود الاستهدافية لجذب المتابعين"""
        TARGETS = ["7alsabe", "faisalsview", "elonmusk", "OpenAI", "sama"]
        for target in TARGETS:
            try:
                user = self.x_client.get_user(username=target).data
                tweets = self.x_client.get_users_tweets(id=user.id, max_results=5).data
                if not tweets: continue
                
                for tweet in tweets:
                    h = hashlib.md5(f"radar_{tweet.id}".encode()).hexdigest()
                    with sqlite3.connect(self.db_path) as conn:
                        if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): continue
                    
                    if any(word in tweet.text.lower() for word in ["ai", "ذكاء", "tech", "تطبيق", "أداة"]):
                        self._smart_engage(tweet, target, h)
                        time.sleep(random.randint(30, 60)) # فاصل بشري بين الردود
                        break
            except: continue

    def _smart_engage(self, tweet, username, h):
        prompt = f"أنت خبير تقني خليجي، رد على تغريدة {username} بذكاء ولباقة. لا توافقه الرأي دائماً إذا كان هناك وجهة نظر تقنية أخرى. اجعل الرد يثير الفضول حول 'أدوات الذكاء الاصطناعي'. التغريدة: {tweet.text}"
        reply = self.brain.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
        self.x_client.create_tweet(text=reply[:275], in_reply_to_tweet_id=tweet.id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now(timezone.utc)))
            conn.commit()

if __name__ == "__main__":
    expert = SovereignExpert()
    expert.fetch_exclusive_news()
    expert.handle_posting()
    expert.handle_radar()
