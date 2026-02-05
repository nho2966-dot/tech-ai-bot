import os, sqlite3, logging, hashlib, time, re, random, json
from datetime import datetime, timezone
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات المؤسسية السيادية ---
load_dotenv()
DB_FILE = "news_enterprise_full_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default"]
}

# الـ Prompts التخصصية
PUBLISH_PROMPT = "أنت محرر تقني مؤسسي. صُغ ثريداً تقنياً احترافياً بالعربية مع مصطلحات إنجليزية بين قوسين. [TWEET_1] افتتاحية، [TWEET_2] تفاصيل تقنية، [POLL_QUESTION] سؤال تفاعلي، [POLL_OPTIONS] خيارات مقسمة بـ (-). لا تستخدم الهاشتاغات."
REPLY_PROMPT = "أنت خبير تقني سيادي. اكتب رداً ذكياً ومختصراً (Smart Reply) يضيف قيمة علمية، مع ذكر مصطلحات إنجليزية بين قوسين. لا ردود عامة."

class TechEliteEnterpriseSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # أوقات الذروة في مسقط (GST) تم تحويلها إلى (UTC) ليفهمها السيرفر
        # مسقط 9ص، 1ظ، 8م، 11م --> UTC 5، 9، 16، 19
        self.peak_hours_utc = [5, 9, 16, 19]

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS editorial_memory (content_hash TEXT PRIMARY KEY, summary TEXT, created_at TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, keywords TEXT)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_peak_time(self):
        """التحقق من وقت الذروة بتوقيت سلطنة عمان"""
        current_hour_utc = datetime.now(timezone.utc).hour
        is_peak = current_hour_utc in self.peak_hours_utc
        if is_peak:
            logging.info(f"🌟 Peak time in Muscat (UTC {current_hour_utc})! High-impact mode enabled.")
        else:
            logging.info(f"⏳ Off-peak in Muscat. Focusing on smart replies only.")
        return is_peak

    def _generate_ai(self, system_p, user_p, h):
        if self._is_in_memory(h): return None
        models = ["qwen/qwen-2.5-72b-instruct", "google/gemini-flash-1.5", "anthropic/claude-3-haiku"]
        
        for model_name in models:
            try:
                logging.info(f"🤖 Attempting with: {model_name}")
                r = self.ai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_p}, {"role": "user", "content": user_p}],
                    temperature=0.3, timeout=40
                )
                content = r.choices[0].message.content
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO editorial_memory VALUES (?, ?, ?)", (h, content[:50], datetime.now().isoformat()))
                return content
            except Exception as e:
                if "429" in str(e): continue
                logging.error(f"🚨 Model {model_name} failed: {e}")
        return None

    def _is_in_memory(self, h):
        with sqlite3.connect(DB_FILE) as conn:
            return conn.execute("SELECT 1 FROM editorial_memory WHERE content_hash=?", (h,)).fetchone() is not None

    def _safe_x_post(self, func, **kwargs):
        try: return func(**kwargs)
        except Exception as e:
            logging.error(f"⚠️ X API Error: {e}")
            return None

    def process_smart_replies(self):
        logging.info("🔍 Searching for smart engagement...")
        queries = ["ذكاء اصطناعي", "الأمن السيبراني", "تقنية"]
        for q in queries:
            tweets = self._safe_x_post(self.x_client.search_recent_tweets, query=f"{q} -is:retweet", max_results=5)
            if not tweets or not tweets.data: continue
            for tweet in tweets.data:
                h = hashlib.sha256(f"rep_{tweet.id}".encode()).hexdigest()
                reply = self._generate_ai(REPLY_PROMPT, tweet.text, h)
                if reply:
                    self._safe_x_post(self.x_client.create_tweet, text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    time.sleep(20)

    def execute_publishing(self):
        posts_done = 0
        for cat, urls in SOURCES.items():
            if posts_done >= 1: break # نشر ثريد واحد دسم في كل دورة ذروة
            for url in urls:
                feed = feedparser.parse(url)
                for entry in feed.entries[:1]:
                    h = hashlib.sha256(entry.title.encode()).hexdigest()
                    content = self._generate_ai(PUBLISH_PROMPT, entry.title, h)
                    if content and self._post_as_thread(content, entry.link):
                        posts_done += 1
                        break

    def _post_as_thread(self, ai_text, url):
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', ai_text, re.S)
        if len(parts) < 3: return False
        last_id = None
        for i, p in enumerate(parts[:3]):
            msg = f"{i+1}/ {p.strip()}"
            if i == 1: msg += f"\n\n🔗 {url}"
            res = self._safe_x_post(self.x_client.create_tweet, text=msg[:280], in_reply_to_tweet_id=last_id)
            if res: last_id = res.data['id']
            time.sleep(15)
        return True

    def run_cycle(self):
        # الردود الذكية تعمل في كل دورة (كل 6 ساعات)
        self.process_smart_replies()
        
        # النشر الاستهدافي يفتح فقط في أوقات الذروة العمانية
        if self._is_peak_time():
            self.execute_publishing()

if __name__ == "__main__":
    TechEliteEnterpriseSystem().run_cycle()
