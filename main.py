import os, sqlite3, logging, hashlib, time, random, textwrap
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- الإعدادات السيادية ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

TARGET_TOPICS = ["أدوات AI", "إنتاجية رقمية", "أمن سيبراني", "أتمتة", "هندسة أوامر", "الثورة الرابعة"]
NEWS_SOURCES = ["https://www.theverge.com/rss/index.xml", "https://www.wired.com/feed/rss"]
CTA_MAP = {"ai_tool": "📌 احفظ الأداة.", "info": "🔁 أعد التغريد.", "scoop": "🚀 تابع للحصريات.", "quiz": "💬 شاركنا رأيك."}
STYLE_MODES = ["3 نقاط قصيرة جداً.", "نقطتان مع مثال عملي.", "نقطة مركزة + تحذير تقني."]
TRUSTED_KEYWORDS = ["official", "announced", "released", "launch", "update", "new"]

class TechSovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 25
        self.last_ai_reset = datetime.now().date()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS content_memory 
                         (h TEXT PRIMARY KEY, h_link TEXT, type TEXT, topic TEXT, monetizable INTEGER DEFAULT 0, dt TEXT)""")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, text_hash TEXT, dt TEXT)")
            conn.execute("""CREATE TABLE IF NOT EXISTS performance 
                         (tweet_id TEXT PRIMARY KEY, type TEXT, likes INTEGER, retweets INTEGER, replies INTEGER, dt TEXT)""")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        if datetime.now().date() != self.last_ai_reset:
            self.ai_calls = 0
            self.last_ai_reset = datetime.now().date()
        if self.ai_calls >= self.MAX_AI_CALLS: return None

        style = random.choice(STYLE_MODES)
        STRICT_SYSTEM = (sys_p + f"\n[صفر هلوسة]. {style} ابدأ بجملة Claim قوية. اذكر المصدر بالاسم.")
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": STRICT_SYSTEM}, {"role": "user", "content": user_p}],
                temperature=0.15
            )
            return r.choices[0].message.content.strip()
        except: return None

    def task_expert_reply(self):
        query = "(\"AI\" OR \"تقنية\" OR #عمان_تتقدم) -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=5, user_auth=True)
            if not tweets or not tweets.data: return False
            for t in tweets.data:
                text_hash = hashlib.sha256(t.text.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=? OR text_hash=?", (str(t.id), text_hash)).fetchone(): continue
                
                reply = self._safe_ai_call("خبير حلول.", f"رد بخطوة عملية واحدة على: {t.text}")
                if reply:
                    final_reply = reply.strip() + "\n\n— Tech Insight"
                    self.x.create_tweet(text=final_reply[:280], in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO tweet_history VALUES (?, ?, ?)", (str(t.id), text_hash, datetime.now().isoformat()))
                    return True
        except: return False
        return False

    def task_scoop_and_content(self):
        weights_dict = {"scoop": 2, "ai_tool": 3, "info": 4, "quiz": 1}
        task_type = random.choices(list(weights_dict.keys()), weights=list(weights_dict.values()))[0]
        topic = random.choice(TARGET_TOPICS)

        content = self._safe_ai_call(f"خبير {topic}.", f"قدم محتوى {task_type} مميز.")
        if content:
            h = hashlib.sha256(content.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO content_memory (h, type, topic, dt) VALUES (?, ?, ?, ?)", 
                             (h, task_type, topic, datetime.now().isoformat()))
            
            # النشر كـ Thread بسيط
            chunks = textwrap.wrap(content, width=250)
            prev_id = None
            for i, chunk in enumerate(chunks):
                if i == len(chunks)-1: chunk += f"\n\n{CTA_MAP.get(task_type, '')}"
                tweet = self.x.create_tweet(text=chunk, in_reply_to_tweet_id=prev_id)
                prev_id = tweet.data['id']
                time.sleep(60)
            return True
        return False

    def run(self):
        if not self.task_expert_reply():
            self.task_scoop_and_content()

if __name__ == "__main__":
    TechSovereignEngine().run()
