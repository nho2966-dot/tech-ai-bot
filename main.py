import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والتحصين ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# أوزان ROI (قياس الأداء)
ROI_WEIGHTS = {
    "like": 1.0,
    "repost": 2.5,
    "reply": 3.0,
    "poll_vote": 1.5
}

ANALYSIS_PROMPT = (
    "أنت خبير استراتيجي في الثورة الصناعية الرابعة (Industry 4.0). "
    "بناءً على نتيجة الاستطلاع التي اختارها الجمهور، قدم تحليلاً ودياً وبسيطاً. "
    "النتيجة الفائزة هي: {winner}. "
    "اشرح للأفراد كيف يستفيدون عملياً من هذا الخيار باستخدام أدوات الذكاء الاصطناعي (AI Tools). "
    "النبرة: رأيكم يهمنا. المصطلحات الإنجليزية بين قوسين."
)

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS active_polls (tweet_id TEXT PRIMARY KEY, topic TEXT, expires_at TEXT, processed INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS roi_metrics (tweet_id TEXT PRIMARY KEY, topic TEXT, content_type TEXT, score REAL, created_at TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _post_poll(self, question, options, topic, reply_to):
        """نشر استطلاع حقيقي وحفظه في القاعدة"""
        try:
            res = self.x.create_tweet(
                text=question[:280],
                in_reply_to_tweet_id=reply_to,
                poll_options=options[:4],
                poll_duration_minutes=1440
            )
            if res:
                poll_id = res.data["id"]
                expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO active_polls VALUES (?, ?, ?, 0)", (poll_id, topic, expires))
                logging.info(f"✅ تم نشر استطلاع حقيقي: {topic}")
                return poll_id
        except Exception as e:
            logging.error(f"❌ خطأ الاستطلاع: {e}")
            return None

    def run_cycle(self):
        # هنا تضع منطق التشغيل الدوري (فحص الأخبار، النشر، التحليل)
        logging.info("🚀 الدورة البرمجية تعمل بنجاح...")
        pass

if __name__ == "__main__":
    bot = TechSupremeSystem()
    bot.run_cycle()
