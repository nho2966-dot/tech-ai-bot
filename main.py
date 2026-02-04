import os, sqlite3, logging, hashlib, time, re, random, json
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlparse

# --- 1. الإعدادات المؤسسية السيادية ---
load_dotenv()
DB_FILE = "news_enterprise_full_2026.db"
STRATEGY_FILE = "strategy_adaptive.json"
ROI_WEIGHTS = {"like": 1.0, "repost": 2.5, "reply": 3.0, "poll_vote": 1.5}

APPROVED_HASHTAGS = {
    "AI_Official": ["#الذكاء_الاصطناعي", "#AI", "#TechNews"],
    "Microsoft_Official": ["#مايكروسوفت", "#أسرار_التقنية", "#MS365"],
    "CyberSecurity": ["#الأمن_السيبراني", "#CyberSecurity", "#InfoSec"]
}

SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default"]
}

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# الـ Prompts التخصصية
PUBLISH_PROMPT = "أنت محرر تقني مؤسسي. صُغ ثريداً تقنياً احترافياً مع مصطلحات إنجليزية بين قوسين. [TWEET_1] هوك، [TWEET_2] تفاصيل تقنية مركزة، [POLL_QUESTION] سؤال تفاعلي، [POLL_OPTIONS] خيارات مقسمة بـ (-). لا تستخدم الهاشتاغات أبداً."
REPLY_PROMPT = "أنت خبير تقني سيادي. اكتب رداً ذكياً ومختصراً (Smart Reply) يضيف قيمة علمية للتغريدة، مع ذكر مصطلحات إنجليزية بين قوسين. تجنب الردود العامة."

class TechEliteEnterpriseSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self._load_strategy()
        self.daily_limit = 4

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS editorial_memory (content_hash TEXT PRIMARY KEY, summary TEXT, created_at TEXT)")
            conn.execute("""CREATE TABLE IF NOT EXISTS roi_metrics (
                                tweet_id TEXT PRIMARY KEY, category TEXT, content_type TEXT,
                                lang TEXT, likes INTEGER, reposts INTEGER, replies INTEGER,
                                polls_votes INTEGER, score REAL, created_at TEXT
                            )""")
            conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, keywords TEXT)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_url ON news(keywords)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roi_created ON roi_metrics(created_at)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _load_strategy(self):
        if os.path.exists(STRATEGY_FILE):
            with open(STRATEGY_FILE, 'r') as f: self.strategy = json.load(f)
        else:
            self.strategy = {"daily_limit": 4, "focus_cats": list(SOURCES.keys()), "last_update": 2026}

    # --- محرك الذكاء المقاوم للزحام (Resilient AI Engine) ---
    def _is_in_memory(self, h):
        with sqlite3.connect(DB_FILE) as conn:
            return conn.execute("SELECT 1 FROM editorial_memory WHERE content_hash=?", (h,)).fetchone() is not None

    def _generate_ai(self, system_p, user_p, h):
        if self._is_in_memory(h): return None
        
        # قائمة النماذج لتجاوز خطأ 429
        models = ["qwen/qwen-2.5-72b-instruct", "google/gemini-flash-1.5", "anthropic/claude-3-haiku"]
        
        for model_name in models:
            retries = 0
            while retries < 2:
                try:
                    r = self.ai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_p}, {"role": "user", "content": user_p}],
                        temperature=0.3
                    )
                    content = r.choices[0].message.content
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO editorial_memory VALUES (?, ?, ?)", (h, content[:50], datetime.now().isoformat()))
                    return content
                except Exception as e:
                    if "429" in str(e):
                        logging.warning(f"⚠️ زحام على {model_name}. محاولة أخرى أو تبديل النموذج...")
                        time.sleep(30)
                        retries += 1
                    else:
                        logging.error(f"🚨 خطأ {model_name}: {e}")
                        break 
        return None

    def _safe_x_post(self, func, **kwargs):
        for i in range(3):
            try: return func(**kwargs)
            except Exception as e:
                logging.error(f"⚠️ X API Error: {e}")
                time.sleep((2**i)*60)
        return None

    # --- [الركن الأول]: النشر الاستهدافي ---
    def post_thread(self, raw_text, url, title, cat):
        ai_text = re.sub(r'[*_>`•]', '', raw_text).strip()
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', ai_text, re.S)
        if len(parts) < 3: return False

        tags = " ".join(random.sample(APPROVED_HASHTAGS.get(cat, ["#Tech"]), 2))
        last_id, poll_id = None, None

        for i, content in enumerate(parts[:3]):
            msg = f"{i+1}/ {content.strip()}"
            if i == 1: msg += f"\n\n🔗 المصدر: {url}"
            if i == 2: msg += f"\n\n{tags}"
            
            if i == 2 and len(parts) >= 4:
                opts = [o.strip()[:25] for o in parts[3].split('-') if 2 <= len(o.strip()) <= 25][:4]
                res = self._safe_x_post(self.x_client.create_tweet, text=msg[:240], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                if res: poll_id = res.data['id']
            else:
                res = self._safe_x_post(self.x_client.create_tweet, text=msg, in_reply_to_tweet_id=last_id)
            
            if res: last_id = res.data['id']
            time.sleep(60)

        if last_id:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO news (hash, title, keywords) VALUES (?, ?, ?)", (hashlib.sha256(title.encode()).hexdigest(), title, url))
                conn.execute("INSERT INTO roi_metrics (tweet_id, category, created_at) VALUES (?, ?, ?)", (str(poll_id or last_id), cat, datetime.now().isoformat()))
            return True
        return False

    # --- [الركن الثاني]: الردود الذكية ---
    def process_smart_replies(self):
        logging.info("🔍 Searching for engagement opportunities...")
        queries = ["ذكاء اصطناعي", "الأمن السيبراني", "تقنيات مايكروسوفت"]
        for q in queries:
            try:
                tweets = self.x_client.search_recent_tweets(query=f"{q} -is:retweet", max_results=5)
                if not tweets.data: continue
                for tweet in tweets.data:
                    h = hashlib.sha256(f"reply_{tweet.id}".encode()).hexdigest()
                    reply_text = self._generate_ai(REPLY_PROMPT, tweet.text, h)
                    if reply_text:
                        self._safe_x_post(self.x_client.create_tweet, text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                        logging.info(f"✅ Smart Reply sent to: {tweet.id}")
                        time.sleep(120)
            except Exception as e:
                logging.error(f"⚠️ Reply Logic Error: {e}")

    # --- الدورة التشغيلية ---
    def run_cycle(self):
        logging.info("🚀 Sovereign Cycle Started")
        self.process_smart_replies() # التفاعل أولاً
        
        posts_count = 0
        for cat, urls in SOURCES.items():
            if posts_count >= self.daily_limit: break
            for url in urls:
                feed = feedparser.parse(url)
                for entry in feed.entries[:2]:
                    h = hashlib.sha256(entry.title.encode()).hexdigest()
                    content = self._generate_ai(PUBLISH_PROMPT, f"{entry.title} - {entry.link}", h)
                    if content and self.post_thread(content, entry.link, entry.title, cat):
                        posts_count += 1
                        time.sleep(600)
        
        logging.info("🏁 Cycle Finished")

    def start_forever(self):
        logging.info("🌍 TechElite Enterprise Engine LIVE 24/7")
        while True:
            try:
                self.run_cycle()
                time.sleep(3600)
            except Exception as e:
                logging.error(f"🚨 Critical Failure: {e}")
                time.sleep(600)

if __name__ == "__main__":
    TechEliteEnterpriseSystem().start_forever()
