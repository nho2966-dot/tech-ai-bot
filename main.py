import os, sqlite3, logging, hashlib, time, random
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والذاكرة ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. المواضيع الستة المستهدفة (الأفراد والترفيه والعملي) ---
TARGET_TOPICS = [
    "الذكاء الاصطناعي للأفراد (ChatGPT, MidJourney, DALL·E, Grok Imagine) وكيفية استخدامه إبداعياً",
    "الهواتف والأجهزة الذكية (Apple, Samsung, Xiaomi) والمقارنات والحيل التقنية",
    "الألعاب الإلكترونية وتقنيات الواقع المعزز (VR/AR) وتجارب الترفيه الرقمي",
    "التطبيقات العملية لإدارة الوقت، الصحة، تعديل الفيديو والتصوير الاحترافي",
    "الأمن الرقمي الشخصي، حماية الخصوصية، تأمين الحسابات، والتعامل مع الاختراقات",
    "التحديات والمسابقات التقنية، ألغاز AI، وتحديات البرمجة"
]

SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://www.technologyreview.com/feed/"
]

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 20  # حصة مرتفعة للحساب المدفوع
        self.AI_RESET_HOUR = 0  # إعادة تعيين الحصة يوميًا عند منتصف الليل
        self.last_reset = datetime.now()
        try:
            me = self.x.get_me()
            self.my_user_id = str(me.data.id)
            logging.info(f"✅ تم التعرف على البوت ID: {self.my_user_id}")
        except: self.my_user_id = None

    # --- 1. قاعدة البيانات ---
    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory ON memory(h)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history ON tweet_history(tweet_id)")
            conn.commit()

    # --- 2. إعداد العملاء ---
    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # --- 3. استدعاء AI بأمان ---
    def _safe_ai_call(self, sys_p, user_p):
        # إعادة ضبط الحصة يوميًا
        if datetime.now().hour == self.AI_RESET_HOUR and (datetime.now() - self.last_reset).days >= 1:
            self.ai_calls = 0
            self.last_reset = datetime.now()
        if self.ai_calls >= self.MAX_AI_CALLS: return None
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
