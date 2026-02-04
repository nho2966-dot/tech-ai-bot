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
PUBLISH_PROMPT = "أنت محرر تقني مؤسسي. صُغ ثريداً تقنياً احترافياً مع مصطلحات إنجليزية بين قوسين. [TWEET_1] هوك، [TWEET_2] تفاصيل، [POLL_QUESTION] سؤال، [POLL_OPTIONS] خيارات (-). لا هاشتاغات."
REPLY_PROMPT = "أنت خبير تقني سيادي. اكتب رداً ذكياً ومختصراً (Smart Reply) يضيف قيمة علمية، مع ذكر مصطلحات إنجليزية بين قوسين. لا ردود عامة."

class TechEliteEnterpriseSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self._load_strategy()
        self.daily_limit = 4

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS editorial_memory (content_hash TEXT PRIMARY KEY, summary TEXT, created_at TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS roi_metrics (tweet_id TEXT PRIMARY KEY, category TEXT, score REAL, created_at TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, keywords TEXT)")

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
            self.strategy = {"daily_limit": 4, "focus_cats": list(SOURCES.keys())}

    # --- محرك الذكاء المقاوم للزحام (Fast-Jump AI Engine) ---
    def _is_in_memory(self, h):
        with sqlite3.connect(DB_FILE) as conn:
            return conn.execute("SELECT 1 FROM editorial_memory WHERE content_hash=?", (h,)).fetchone() is not None

    def _generate_ai(self, system_p, user_p, h):
        if self._is_in_memory(h): return None
        
        # نماذج متنوعة لتجنب تعليق الـ Action عند وجود زحام (429)
        models = [
            "qwen/qwen-2.5-72b-instruct", 
            "google/gemini-flash-1.5", 
            "anthropic/claude-3-haiku",
            "openai/gpt-4o-mini"
        ]
        
        for model_name in models:
            try:
                logging.info(f"🤖 Trying: {model_name}")
                r = self.ai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_p}, {"role": "user", "content": user_p}],
                    temperature=0.3,
                    timeout=45 
                )
                content = r.choices[0].message.content
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO editorial_memory VALUES (?, ?, ?)", (h, content[:50], datetime.now().isoformat()))
                return content
            except Exception as e:
                if "429" in str(e):
                    logging.warning(f"⚠️ {model_name} busy. Jumping to next...")
                    continue 
                logging.error(f"🚨 Model {model_name} failed: {e}")
                continue
        return None

    def _safe_x_post(self, func, **kwargs):
        for i in range(2): # تقليل المحاولات لسرعة التنفيذ
            try: return func(**kwargs)
            except: time.sleep(30)
        return None

    # --- [الركن الأول]: النشر الاستهدافي ---
    def post_thread(self, raw_text, url, title, cat):
        ai_text = re.sub(r'[*_>`•]', '', raw_text).strip()
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', ai_text, re.S)
        if len(parts) < 3: return False

        tags = " ".join(random.sample(APPROVED_HASHTAGS.get(cat, ["#Tech"]), 2))
        last_id = None

        for i, content in enumerate(parts[:3]):
            msg = f"{i+1}/ {content.strip()}"
            if i == 1: msg += f"\n\n🔗 Source: {url}"
            if i == 2: msg += f"\n\n{tags}"
            
            res = self._safe_x_post(self.x_client.create_tweet, text=msg[:280], in_reply_to_tweet_id=last_id)
            if res: last_id = res.data['id']
            time.sleep(10)

        return True if last_id else False

    # --- [الركن الثاني]: الردود الذكية ---
    def process_smart_replies(self):
        logging.info("🔍 Engagement Mode Active...")
        queries = ["ذكاء اصطناعي", "الأمن السيبراني", "Microsoft 365"]
        for q in queries:
            try:
                tweets = self.x_client.search_recent_tweets(query=f"{q} -is:retweet", max_results=5)
                if not tweets.data: continue
                for tweet in tweets.data:
                    h = hashlib.sha256(f"rep_{tweet.id}".encode()).hexdigest()
                    reply = self._generate_ai(REPLY_PROMPT, tweet.text, h)
                    if reply:
                        self._safe_x_post(self.x_client.create_tweet, text=reply[:280], in_reply_to_tweet_id=tweet.id)
                        logging.info(f"✅ Replied to: {tweet.id}")
                        time.sleep(30)
            except: continue

    def run_cycle(self):
        logging.info("🚀 Sovereign Cycle Execution")
        self.process_smart_replies() 
        
        posts_count = 0
        for cat, urls in SOURCES.items():
            if posts_count >= self.daily_limit: break
            for url in urls:
                feed = feedparser.parse(url)
                for entry in feed.entries[:2]:
                    h = hashlib.sha256(entry.title.encode()).hexdigest()
                    content = self._generate_ai(PUBLISH_PROMPT, entry.title, h)
                    if content and self.post_thread(content, entry.link, entry.title, cat):
                        posts_count += 1
                        time.sleep(60)

if __name__ == "__main__":
    # تشغيل دورة واحدة ليتناسب مع GitHub Actions
    TechEliteEnterpriseSystem().run_cycle()
