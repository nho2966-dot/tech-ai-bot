import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والتحصين ---
load_dotenv()
DB_FILE = "news_enterprise_full_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default"]
}

PUBLISH_PROMPT = "أنت محرر تقني مؤسسي رصين. صُغ ثريداً تقنياً احترافياً بالعربية مع مصطلحات إنجليزية بين قوسين. [TWEET_1] تحليل، [TWEET_2] تفاصيل، [POLL_QUESTION] سؤال، [POLL_OPTIONS] خيارات (-). لا هاشتاغات."
REPLY_PROMPT = "أنت خبير تقني في عمان. رد بذكاء واختصار، أضف قيمة علمية، استخدم مصطلحات إنجليزية بين قوسين."

class TechEliteEnterpriseSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # ساعات الذروة في عمان (GST)
        self.peak_hours_utc = [4, 5, 9, 16, 19] 

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS editorial_memory (content_hash TEXT PRIMARY KEY, summary TEXT, category TEXT, created_at TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS performance_metrics (tweet_id TEXT PRIMARY KEY, category TEXT, likes INTEGER DEFAULT 0, retweets INTEGER DEFAULT 0, last_updated TEXT)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _check_x_health(self) -> bool:
        try:
            self.x_client.get_me()
            return True
        except Exception as e:
            logging.error(f"🚨 X API Connection Issue: {e}")
            return False

    def _safe_x_post(self, **kwargs):
        for attempt in range(3):
            try: 
                return self.x_client.create_tweet(**kwargs)
            except tweepy.errors.TooManyRequests:
                logging.warning("⚠️ Post Rate Limit Hit. Waiting 60s...")
                time.sleep(60)
            except Exception as e: 
                logging.error(f"❌ Post Failed: {e}")
                return None
        return None

    def test_connection_post(self):
        """دالة لإرسال تغريدة اختبار فورية للتأكد من صلاحيات الكتابة"""
        h = hashlib.sha256("test_initial_boot".encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM editorial_memory WHERE content_hash=?", (h,)).fetchone():
                return
        
        test_msg = "🛡️ تم تفعيل نظام الإدارة التقنية المؤسسية (Enterprise Tech System) بنجاح. خوارزميات النشر والرد الذكي قيد التشغيل الآن. 🇴🇲"
        res = self._safe_x_post(text=test_msg)
        if res:
            logging.info("✅ Test Tweet Sent Successfully!")
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO editorial_memory VALUES (?, ?, ?, ?)", (h, "Initial Boot Test", "System", datetime.now().isoformat()))

    def process_smart_replies(self):
        logging.info("🔍 Deep Engagement Mode...")
        queries = ["الذكاء الاصطناعي", "الأمن السيبراني", "التحول الرقمي عمان"]
        for q in queries:
            try:
                tweets = self.x_client.search_recent_tweets(query=f"{q} -is:retweet", max_results=10, user_auth=True)
                if not tweets or not tweets.data: continue
                for tweet in tweets.data:
                    if not tweet.author_id or self._recently_replied(tweet.author_id): continue
                    h = hashlib.sha256(f"rep_{tweet.id}".encode()).hexdigest()
                    reply = self._generate_ai(REPLY_PROMPT, tweet.text, h, "Engagement", f"user_{tweet.author_id}")
                    if reply:
                        self._safe_x_post(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                        time.sleep(20)
            except tweepy.errors.TooManyRequests:
                logging.warning(f"⚠️ Search limit reached for '{q}'. Skipping...")
                continue

    def execute_publishing(self, force=False):
        # تجاوز شرط الوقت إذا كان force=True
        current_hour = datetime.now(timezone.utc).hour
        if not force and current_hour not in self.peak_hours_utc:
            logging.info(f"🕒 Not peak hour ({current_hour} UTC). Skipping publication.")
            return

        logging.info("🌟 Publishing started...")
        for cat, urls in SOURCES.items():
            for rss in urls:
                feed = feedparser.parse(rss)
                for entry in feed.entries[:1]: # نشر خبر واحد من كل مصدر للاختبار
                    if not hasattr(entry, "link"): continue
                    h = hashlib.sha256(f"{entry.title}{entry.link}".encode()).hexdigest()
                    content = self._generate_ai(PUBLISH_PROMPT, entry.title, h, cat)
                    if content: self._post_thread(content, entry.link, cat)

    def _post_thread(self, ai_text, url, category):
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', ai_text, re.S)
        last_id = None
        for i, p in enumerate(parts[:3]):
            msg = f"{i+1}/ {p.strip()}"
            if i == 1: msg += f"\n\n🔗 {url}"
            res = self._safe_x_post(text=msg[:280], in_reply_to_tweet_id=last_id)
            if res:
                last_id = res.data["id"]
                if i == 0:
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT OR IGNORE INTO performance_metrics (tweet_id, category, last_updated) VALUES (?, ?, ?)",
                                     (str(last_id), category, datetime.now().isoformat()))
            time.sleep(15)

    def _generate_ai(self, system_p, user_p, h, category, summary_label=None):
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM editorial_memory WHERE content_hash=?", (h,)).fetchone(): return None
        try:
            r = self.ai_client.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", 
                messages=[{"role": "system", "content": system_p}, {"role": "user", "content": user_p}], temperature=0.3)
            content = r.choices[0].message.content
            label = summary_label or content[:50]
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO editorial_memory VALUES (?, ?, ?, ?)", (h, label, category, datetime.now().isoformat()))
            return content
        except: return None

    def _recently_replied(self, author_id) -> bool:
        with sqlite3.connect(DB_FILE) as conn:
            one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
            row = conn.execute("SELECT 1 FROM editorial_memory WHERE summary=? AND created_at>?", (f"user_{author_id}", one_day_ago)).fetchone()
            return row is not None

    def run_cycle(self):
        if not self._check_x_health(): return
        
        # 1. اختبار الإرسال الفوري (سيعمل لمرة واحدة فقط)
        self.test_connection_post()
        
        # 2. محاولة التفاعل مع الآخرين
        self.process_smart_replies()
        
        # 3. النشر الإجباري لمرة واحدة للتأكد من المحتوى (تم وضع force=True)
        self.execute_publishing(force=True)

if __name__ == "__main__":
    TechEliteEnterpriseSystem().run_cycle()
