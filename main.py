import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

# ضبط الرقابة الاستراتيجية
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignZenithV72:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        # مصادر النخبة التقنية العالمية
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss",
            "https://arstechnica.com/feed/",
            "https://9to5mac.com/feed/",
            "https://9to5google.com/feed/"
        ]
        # ميثاق عمالقة الصناعة الرابعة (تجنب الهلوسة والالتزام بالخليجية)
        self.charter = (
            "أنت المستشار التقني الأعلى. فكرك يجمع بين الهندسة والرؤية الاستراتيجية.\n"
            "1. الهوية: لغة خليجية نُخبوية بيضاء رصينة، مصطلحات تقنية بين قوسين ().\n"
            "2. المهام: (تحليل الخبر + المقارنة التنافسية + الأثر على السيادة الرقمية والخصوصية للفرد).\n"
            "3. الفلاتر الصارمة: صفر هلوسة (دقة 100%)، منع الأخبار القديمة (>36س)، منع الرد على النفس أو تكرار الرد."
        )

    def _init_db(self):
        with sqlite3.connect("sovereign_zenith.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        # تفعيل وضع الانتظار الرسمي لتجنب الحظر
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _strategic_thinker(self, prompt, context=""):
        """محرك التفكير الاستباقي وفحص الحقائق"""
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.1 # انضباط كامل لمنع الهلوسة
            ).choices[0].message.content.strip()
            # فلتر النقاء اللغوي
            if re.match(r'^[ \u0600-\u06FF0-9a-zA-Z()\[\]\.\!\?\-\n\r]+$', res):
                return res
            return ""
        except Exception as e:
            logging.error(f"AI Brain Error: {e}")
            return ""

    def _is_throttled(self, task, minutes):
        """إدارة ذكية للموارد لضمان الاستدامة"""
        with sqlite3.connect("sovereign_zenith.db") as conn:
            res = conn.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
