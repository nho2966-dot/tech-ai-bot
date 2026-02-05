import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والتحصين المؤسسي ---
load_dotenv()
DB_FILE = "news_enterprise_full_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# مصادر تقنية Tier-1
SOURCES = {
    "AI_Official": [
        "https://blog.google/technology/ai/rss/",
        "https://openai.com/news/rss/"
    ],
    "Microsoft_Official": [
        "https://www.microsoft.com/en-us/microsoft-365/blog/feed/"
    ],
    "CyberSecurity": [
        "https://thehackernews.com/feeds/posts/default"
    ]
}

# Prompts
PUBLISH_PROMPT = (
    "أنت محرر تقني مؤسسي رصين. صُغ ثريداً تقنياً احترافياً بالعربية مع مصطلحات إنجليزية بين قوسين. "
    "[TWEET_1] تحليل للخبر، "
    "[TWEET_2] تفاصيل تقنية عميقة، "
    "[POLL_QUESTION] سؤال استراتيجي، "
    "[POLL_OPTIONS] خيارات (-). "
    "لا هاشتاغات."
)

REPLY_PROMPT = (
    "أنت خبير تقني سيادي في سلطنة عمان. "
    "رد بذكاء واختصار، أضف قيمة علمية، "
    "استخدم مصطلحات إنجليزية بين قوسين، "
    "واحفظ نبرة مهنية مؤسسية."
)


class TechEliteEnterpriseSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # ذروة مسقط (GST) → UTC
        self.peak_hours_utc = [5, 9, 16, 19]

    # ---------------- DB ----------------
    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS editorial_memory (
                    content_hash TEXT PRIMARY KEY,
                    summary TEXT,
                    category TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    tweet_id TEXT PRIMARY KEY,
                    category TEXT,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    last_updated TEXT
                )
            """)

    # ---------------- Clients ----------------
    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    # ---------------- Safety / Compliance ----------------
    def _check_x_health(self) -> bool:
        """
        Circuit Breaker:
        إيقاف البوت فورًا عند تغيّر سياسات X أو فقدان صلاحيات
        """
        try:
            self.x_client.get_me()
            return True
        except Exception as e:
            msg = str(e).lower()
            if "forbidden" in msg or "policy" in msg or "permission" in msg:
                logging.error("🚨 X Policy / Permission Change Detected → AUTO-PAUSE")
                return False
            logging.warning(f"⚠️ X API unstable: {e}")
            return False

    def _safe_x_post(self, **kwargs):
        for attempt in range(3):
            try:
                return self.x_client.create_tweet(**kwargs)
            except Exception as e:
                if "429" in str(e):
                    time.sleep(60 * (attempt + 1))
                else:
                    logging.error(f"X Post Failed: {e}")
                    return None
        return None

    # ---------------- Filters ----------------
    def _is_technical_news(self, title: str) -> bool:
        keywords = [
            "ai", "model", "security", "cloud", "data",
            "update", "research", "ذكاء", "أمن", "سحابة", "بيانات"
        ]
        matches = sum(k in title.lower() for k in keywords)
        return matches >= 2

    def _recently_replied(self, author_id) -> bool:
        with sqlite3.connect(DB_FILE) as conn:
            one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
            row = conn.execute(
                "SELECT 1 FROM editorial_memory WHERE summary=? AND created_at>?",
                (f"user_{author_id}", one_day_ago)
            ).fetchone()
            return row is not None

    # ---------------- ROI Engine ----------------
    def _update_performance_metrics(self):
        with sqlite3.connect(DB_FILE) as conn:
            rows = conn.execute(
                "SELECT tweet_id FROM performance_metrics "
                "ORDER BY last_updated ASC LIMIT 5"
            ).fetchall()

        for (tweet_id,) in rows:
            try:
                res = self.x_client.get_tweet(
                    id=tweet_id,
                    tweet_fields=["public_metrics"]
                )
                if res and res.data:
                    m = res.data.public_metrics
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("""
                            UPDATE performance_metrics
                            SET likes=?, retweets=?, last_updated=?
                            WHERE tweet_id=?
                        """, (
                            m["like_count"],
                            m["retweet_count"],
                            datetime.now().isoformat(),
                            tweet_id
                        ))
                time.sleep(5)
            except:
                continue

    def _get_best_category(self) -> str:
        with sqlite3.connect(DB_FILE) as conn:
            row = conn.execute("""
                SELECT category
                FROM performance_metrics
                GROUP BY category
                ORDER BY SUM(likes + retweets) DESC
                LIMIT 1
            """).fetchone()
            return row[0] if row else "AI_Official"

    # ---------------- AI ----------------
    def _generate_ai(self, system_p, user_p, h, category, summary_label=None):
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute(
                "SELECT 1 FROM editorial_memory WHERE content_hash=?",
                (h,)
            ).fetchone():
                return None

        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": system_p},
                    {"role": "user", "content": user_p}
                ],
                temperature=0.3
            )
            content = r.choices[0].message.content
            label = summary_label or content[:50]

            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("""
                    INSERT INTO editorial_memory
                    VALUES (?, ?, ?, ?)
                """, (
                    h, label, category,
                    datetime.now().isoformat()
                ))
            return content
        except Exception as e:
            logging.error(f"AI Generation Failed: {e}")
            return None

    # ---------------- Engagement ----------------
    def process_smart_replies(self):
        logging.info("🔍 Deep Engagement Mode...")
        queries = [
            "الذكاء الاصطناعي",
            "الأمن السيبراني",
            "التحول الرقمي عمان"
        ]

        for q in queries:
            tweets = self.x_client.search_recent_tweets(
                query=f"{q} -is:retweet",
                max_results=5,
                user_auth=True
            )
            if not tweets or not tweets.data:
                continue

            for tweet in tweets.data:
                if not tweet.author_id:
                    continue
                if self._recently_replied(tweet.author_id):
                    continue

                h = hashlib.sha256(
                    f"rep_{tweet.id}".encode()
                ).hexdigest()

                reply = self._generate_ai(
                    REPLY_PROMPT,
                    tweet.text,
                    h,
                    "Engagement",
                    f"user_{tweet.author_id}"
                )
                if reply:
                    self._safe_x_post(
                        text=reply[:280],
                        in_reply_to_tweet_id=tweet.id
                    )
                    time.sleep(25)

    # ---------------- Publishing ----------------
    def execute_publishing(self):
        best_cat = self._get_best_category()
        logging.info(f"🌟 Peak Publishing → Focus: {best_cat}")

        for cat, urls in SOURCES.items():
            limit = 2 if cat == best_cat else 1
            for rss in urls:
                feed = feedparser.parse(rss)
                for entry in feed.entries[:limit]:
                    if not hasattr(entry, "link"):
                        continue
                    if not self._is_technical_news(entry.title):
                        continue

                    h = hashlib.sha256(
                        f"{entry.title}{entry.link}".encode()
                    ).hexdigest()

                    content = self._generate_ai(
                        PUBLISH_PROMPT,
                        entry.title,
                        h,
                        cat
                    )
                    if content:
                        self._post_thread(content, entry.link, cat)

    def _post_thread(self, ai_text, url, category):
        parts = re.findall(
            r'\[.*?\](.*?)(?=\[|$)',
            ai_text,
            re.S
        )
        last_id = None

        for i, p in enumerate(parts[:3]):
            msg = f"{i+1}/ {p.strip()}"
            if i == 1:
                msg += f"\n\n🔗 {url}"

            res = self._safe_x_post(
                text=msg[:280],
                in_reply_to_tweet_id=last_id
            )

            if res:
                last_id = res.data["id"]
                if i == 0:
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("""
                            INSERT OR IGNORE INTO performance_metrics
                            (tweet_id, category, last_updated)
                            VALUES (?, ?, ?)
                        """, (
                            str(last_id),
                            category,
                            datetime.now().isoformat()
                        ))
            time.sleep(15)

    # ---------------- Cycle ----------------
    def run_cycle(self):
        if not self._check_x_health():
            return

        self._update_performance_metrics()
        self.process_smart_replies()

        if datetime.now(timezone.utc).hour in self.peak_hours_utc:
            self.execute_publishing()


if __name__ == "__main__":
    TechEliteEnterpriseSystem().run_cycle()
