import os, sqlite3, logging, hashlib, time, re, random, requests
import tweepy, feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()
DB_FILE = "news.db"

# 1️⃣ الدليل التحريري والبرومبت المؤسسي
AUTHORITY_PROMPT = """
أنت رئيس تحرير في وكالة (TechElite). صُغ المحتوى بناءً على [النوع الإلزامي] المرفق.
القواعد: ممنوع الاستنتاج، ممنوع صفات المدح، التزام تام بالحقائق، النبرة باردة ورصينة، المصطلحات الإنجليزية بين قوسين (Term).
"""

class TechEliteAuthority:
    STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "new", "update", "report"}
    AR_STOP = {"من", "في", "على", "إلى", "عن", "تم", "كما", "وفق", "حيث", "بعد", "هذا", "خلال", "بناء"}
    CORE_TERMS = {"ai", "chip", "gpu", "ios", "android", "iphone", "nvidia", "m4", "snapdragon", "openai"}
    SOURCE_TRUST = {"theverge.com": "موثوق", "9to5mac.com": "موثوق", "techcrunch.com": "موثوق", "bloomberg.com": "عالي الموثوقية"}
    MAX_TWEETS_BY_TYPE = {"إطلاق": 3, "تحديث": 2, "تسريب": 2, "تقرير": 2}

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()
        self.my_id = None

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS decisions (hash TEXT PRIMARY KEY, decision TEXT, reason TEXT, timestamp TEXT)")
        conn.commit(); conn.close()

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        auth = tweepy.OAuth1UserHandler(os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"), os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET"))
        self.x_api_v1 = tweepy.API(auth)
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")

    # --- حوكمة الحقائق ---
    def fact_overlap_guard(self, ai_text, source_text):
        ai_words = set(re.findall(r'\w+', ai_text.lower())) - self.AR_STOP
        src_words = set(re.findall(r'\w+', source_text.lower())) - self.AR_STOP
        if not ai_words: return True
        diff = len(ai_words - src_words) / len(ai_words)
        return diff < 0.20

    def pre_classify(self, title):
        t = title.lower()
        if any(x in t for x in ["launch", "announce", "reveal"]): return "إطلاق"
        if any(x in t for x in ["update", "version", "ios", "beta"]): return "تحديث"
        if any(x in t for x in ["leak", "rumor", "spotted"]): return "تسريب"
        return "تقرير"

    # --- محرك التفاعل (الردود والاستطلاعات) ---
    def handle_smart_replies(self):
        try:
            if not self.my_id: self.my_id = str(self.x_client.get_me().data.id)
            mentions = self.x_client.get_users_mentions(id=self.my_id, max_results=5)
            if not mentions.data: return
            
            conn = sqlite3.connect(DB_FILE)
            for tweet in mentions.data:
                h = f"rep_{tweet.id}"
                if conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone(): continue
                
                prompt = "أنت خبير تقني سعودي. رد بلهجة بيضاء رصينة ومختصرة جداً. ممنوع الهلوسة."
                reply = self._generate_ai(prompt, f"استفسار المتابع: {tweet.text}")
                if reply:
                    self.x_client.create_tweet(text=reply[:278], in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, "reply", datetime.now().isoformat()))
                    conn.commit()
            conn.close()
        except Exception as e: logging.error(f"Reply Error: {e}")

    def handle_engagement_polls(self):
        """توليد استطلاع رأي بناءً على آخر خبر منشور"""
        try:
            conn = sqlite3.connect(DB_FILE)
            last = conn.execute("SELECT title FROM news WHERE hash NOT LIKE 'rep_%' ORDER BY published_at DESC LIMIT 1").fetchone()
            conn.close()
            if not last: return

            prompt = f"بناءً على الخبر: ({last[0]})\nصُغ سؤال استطلاع رأي تقني محايد مع 3 خيارات قصيرة جداً.\nالتنسيق: السؤال في سطر والخيارات في الأسطر التالية."
            res = self._generate
