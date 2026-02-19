import os
import time
import random
import sqlite3
import logging
import hashlib
import re
from datetime import datetime
import tweepy
import requests
from google import genai
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="🛡️ [APEX MEDIA]: %(message)s")

DB_PATH = "data/apex_media.db"
MAX_TWEET_LENGTH = 280


class ApexMediaSystem:

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()
        self._init_clients()

        self.brains = [
            {"name": "Gemini", "type": "google", "model": "gemini-2.0-flash", "env": "GEMINI_KEY"},
            {"name": "Grok", "type": "xai", "model": "grok-2-latest", "env": "XAI_API_KEY"},
            {"name": "OpenAI", "type": "openai", "model": "gpt-4o", "env": "OPENAI_API_KEY"},
        ]

        self.tech_keywords = [
            "ai","iphone","android","openai","google","chip",
            "gpu","device","update","chatgpt","tesla"
        ]

        self.angles = [
            "شرح مبسط للمستخدم",
            "تحليل تقني عميق",
            "تحذير أمني",
            "زاوية لا يتحدث عنها أحد",
            "توقع مستقبلي"
        ]

    # =========================================================
    # DATABASE
    # =========================================================
    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:

            conn.execute("""
            CREATE TABLE IF NOT EXISTS history(
                hash TEXT PRIMARY KEY,
                ts DATETIME
            )""")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS performance(
                id TEXT PRIMARY KEY,
                category TEXT,
                likes INTEGER,
                replies INTEGER,
                ts DATETIME
            )""")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS trend_memory(
                keyword TEXT PRIMARY KEY,
                score INTEGER,
                last_seen DATETIME
            )""")

    # =========================================================
    # CLIENTS
    # =========================================================
    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # =========================================================
    # CLEAN + DUPLICATE
    # =========================================================
    def _clean(self, text):
        text = re.sub(r'[\*\#\_\[\]\(\)\~\`\>]', '', text)
        return " ".join(text.split())[:MAX_TWEET_LENGTH]

    def _is_duplicate(self, text):
        h = hashlib.sha256(text.encode()).hexdigest()
        with sqlite3.connect(DB_PATH) as conn:
            if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                return True
            conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.utcnow()))
        return False

    # =========================================================
    # BRAIN ENGINE
    # =========================================================
    def generate(self, prompt):

        for brain in self.brains:
            api_key = os.getenv(brain["env"])
            if not api_key:
                continue

            try:
                logging.info(f"🧠 {brain['name']}")

                if brain["type"] == "google":
                    client = genai.Client(api_key=api_key)
                    res = client.models.generate_content(
                        model=brain["model"],
                        contents=prompt
                    )
                    text = res.text

                else:
                    base = "https://api.x.ai/v1" if brain["type"] == "xai" else None
                    client = OpenAI(api_key=api_key, base_url=base)
                    res = client.chat.completions.create(
                        model=brain["model"],
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=280
                    )
                    text = res.choices[0].message.content

                cleaned = self._clean(text)

                if len(cleaned) < 40:
                    raise Exception("Low quality")

                return cleaned

            except Exception:
                continue

        return "تدري؟ أحيانًا أبسط إعداد تقني مخفي يغير تجربتك بالكامل."

    # =========================================================
    # TREND ANALYSIS
    # =========================================================
    def analyze_trend_text(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        matched = [w for w in words if w in self.tech_keywords]

        with sqlite3.connect(DB_PATH) as conn:
            for word in matched:
                conn.execute("""
                INSERT INTO trend_memory VALUES (?,1,?)
                ON CONFLICT(keyword)
                DO UPDATE SET
                    score = score + 1,
                    last_seen = ?
                """,(word, datetime.utcnow(), datetime.utcnow()))

    def detect_content_gap(self):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT keyword FROM trend_memory
            ORDER BY score DESC
            LIMIT 5
            """)
            rows = cur.fetchall()

        if rows:
            return random.choice(rows)[0]

        return random.choice(self.tech_keywords)

    # =========================================================
    # PERFORMANCE
    # =========================================================
    def record_performance(self, tweet_id, category):
        try:
            metrics = self.x_client.get_tweet(
                tweet_id,
                tweet_fields=["public_metrics"]
            )

            if metrics.data:
                m = metrics.data.public_metrics

                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("""
                    INSERT OR REPLACE INTO performance
                    VALUES (?, ?, ?, ?, ?)
                    """,(
                        tweet_id,
                        category,
                        m["like_count"],
                        m["reply_count"],
                        datetime.utcnow()
                    ))
        except:
            pass

    def predict_engagement(self, category):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT AVG(likes + replies)
            FROM performance
            WHERE category=?
            """,(category,))
            avg = cur.fetchone()[0]

        return avg or 0

    # =========================================================
    # SAFE POST
    # =========================================================
    def safe_post(self, text):
        for attempt in range(3):
            try:
                return self.x_client.create_tweet(text=text)
            except Exception:
                time.sleep((2**attempt)*5)
        return None

    # =========================================================
    # MAIN MEDIA LOOP
    # =========================================================
    def run(self):

        category = self.detect_content_gap()
        angle = random.choice(self.angles)

        predicted = self.predict_engagement(category)

        prompt = f"""
        أنت منصة إعلام تقني خليجية.
        اكتب محتوى احترافي.
        الزاوية: {angle}
        الموضوع: {category}
        بدون رموز.
        """

        content = self.generate(prompt)

        if self._is_duplicate(content):
            logging.info("⚠️ مكرر")
            return

        if predicted < 1:
            logging.info("📉 توقع منخفض لكن سيتم الاختبار")

        result = self.safe_post(content)

        if result:
            self.record_performance(result.data["id"], category)
            logging.info("🚀 نشر محتوى إعلامي بنجاح")


if __name__ == "__main__":
    system = ApexMediaSystem()
    system.run()
