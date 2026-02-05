import os, sqlite3, logging, hashlib, time, random
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

# المصادر والمواضيع
BREAKING_SOURCES = ["https://www.theverge.com/rss/index.xml", "https://www.wired.com/feed/rss"]
CORE_TOPICS = ["الذكاء الاصطناعي (AI Tools)", "الطباعة ثلاثية الأبعاد (3D Printing)", "إنترنت الأشياء (IoT)", "الأجهزة الذكية (Smart Devices)"]

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.MAX_AI_CALLS = 18
        self.ai_calls = 0

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (user_id TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        try:
            self.my_id = str(self.x.get_me().data.id)
        except: self.my_id = None

    def _safe_ai_call(self, sys_p, user_p):
        if self.ai_calls >= self.MAX_AI_CALLS: return None
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": sys_p + " قيد: لا هلوسة، حقائق فقط، مصطلحات إنجليزية بين قوسين."}, {"role": "user", "content": user_p}],
                temperature=0.2
            )
            return r.choices[0].message.content
        except Exception as e:
            logging.error(f"❌ AI Error: {e}"); return None

    # --- دالة الردود الذكية (المفقودة التي سببت الخطأ) ---
    def process_smart_replies(self):
        logging.info("🔍 فحص الردود الذكية...")
        query = "(\"كيف أستخدم AI\" OR #عمان_تتقدم OR \"الأجهزة الذكية\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=10, user_auth=True)
            if not tweets or not tweets.data: return
            for t in tweets.data[:3]:
                if str(t.author_id) == self.my_id: continue
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=?", (str(t.id),)).fetchone(): continue
                
                reply = self._safe_ai_call("خبير تقني. رد بممارسة عمليّة دقيقة (Industry 4.0).", t.text)
                if reply:
                    time.sleep(10)
                    self.x.create_tweet(text=reply[:280], in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO tweet_history VALUES (?, ?)", (str(t.id), datetime.now().isoformat()))
                        conn.commit()
        except Exception as e: logging.error(f"❌ خطأ الردود: {e}")

    def execute_strategic_flow(self):
        # سبق صحفي
        for url in BREAKING_SOURCES:
            feed = feedparser.parse(url)
            if feed.entries:
                latest = feed.entries[0]
                h = hashlib.sha256(latest.title.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if not conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        content = self._safe_ai_call("🚨 سبق تقني:", latest.title)
                        if content:
                            self.x.create_tweet(text=f"🚨 سبق تقني: {content[:240]} #عمان_تتقدم")
                            with sqlite3.connect(DB_FILE) as conn:
                                conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                            return

        # مسابقة أو محتوى اعتيادي
        now = datetime.now()
        if now.weekday() == 3: # الخميس
            self.x.create_tweet(text="🏆 مسابقة الأسبوع التقنية حانت! ترقبوا السؤال في الرد القادم.")
        else:
            topic = random.choice(CORE_TOPICS)
            content = self._safe_ai_call(f"صغ ممارسة عملية حول {topic}.", "تحديث تقني")
            if content: self.x.create_tweet(text=f"📌 {content[:270]}")

    def run(self):
        self.process_smart_replies()
        time.sleep(15)
        self.execute_strategic_flow()

if __name__ == "__main__":
    TechSupremeSystem().run()
