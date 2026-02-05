import os, sqlite3, logging, hashlib, time, random
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والذاكرة ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. المجالات الستة المستهدفة للأفراد ---
TARGET_TOPICS = [
    "الذكاء الاصطناعي للأفراد (ChatGPT, MidJourney) واستخداماته الإبداعية",
    "الهواتف والأجهزة الذكية (Apple, Samsung) والحيل التقنية",
    "الألعاب الإلكترونية وتقنيات (VR/AR) والترفيه الرقمي",
    "التطبيقات العملية لإدارة الوقت، الصحة، وتعديل الفيديو",
    "الأمن الرقمي الشخصي وحماية الخصوصية من الاختراقات",
    "التحديات والمسابقات التقنية وألغاز AI"
]

SOURCES = ["https://www.theverge.com/rss/index.xml", "https://www.wired.com/feed/rss"]

class TechSupremeProfessional:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 25
        try:
            me = self.x.get_me()
            self.my_user_id = str(me.data.id)
        except: self.my_user_id = None

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": sys_p + " قيد: العربية، مصطلحات إنجليزية، لا هلوسة، نقاط مركزة."},
                    {"role": "user", "content": user_p}
                ],
                temperature=0.2
            )
            return r.choices[0].message.content
        except: return None

    # --- 3. نظام النشر المتزن (Throttled Threading) ---
    def _publish_safe_thread(self, content, prefix=""):
        # تقسيم المحتوى بذكاء لتجنب الحظر
        chunks = [content[i:i+250] for i in range(0, len(content), 250)]
        prev_id = None
        for i, chunk in enumerate(chunks):
            try:
                text = f"{prefix if i==0 else ''}{chunk}"
                tweet = self.x.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
                prev_id = tweet.data['id']
                logging.info(f"✅ تم نشر جزء {i+1}")
                time.sleep(45) # انتظار طويل نسبياً بين أجزاء السلسلة لتهدئة API
            except tweepy.errors.TooManyRequests:
                logging.warning("🚨 X API Limit reached. Stopping thread.")
                break

    # --- 4. المهام المنفصلة ---
    def task_scoop(self):
        logging.info("🔎 فحص السبق الصحفي...")
        for url in SOURCES:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            latest = feed.entries[0]
            h = hashlib.sha256(latest.title.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
            
            content = self._safe_ai_call("🚨 سبق تقني:", f"حلل الخبر [{latest.title}] للأفراد.")
            if content:
                self._publish_safe_thread(content, "🚨 سبق تقني عاجل:\n")
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                return True
        return False

    def task_reply(self):
        logging.info("💬 فحص الردود الذكية...")
        query = "(#عمان_تتقدم OR \"كيف أستخدم AI\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=10, user_auth=True)
            if tweets.data:
                for t in tweets.data:
                    with sqlite3.connect(DB_FILE) as conn:
                        if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=?", (str(t.id),)).fetchone(): continue
                    
                    reply = self._safe_ai_call("خبير تقني 4.0.", t.text)
                    if reply:
                        self.x.create_tweet(text=f"{reply[:280]}", in_reply_to_tweet_id=t.id)
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT INTO tweet_history VALUES (?, ?)", (str(t.id), datetime.now().isoformat()))
                        logging.info(f"✅ تم الرد على {t.id}")
                        return True # رد واحد فقط في الدورة الواحدة للأمان
        except: pass
        return False

    def task_regular_post(self):
        logging.info("💡 نشر محتوى مجدول...")
        topic = random.choice(TARGET_TOPICS)
        content = self._safe_ai_call(f"صغ ممارسة في {topic}.", "محتوى اليوم")
        if content:
            self._publish_safe_thread(content, "💡 تجربة تقنية:\n")
            return True
        return False

    # --- 5. المحرك الاحترافي (The Strategy) ---
    def run_strategy(self):
        # موازنة المهام: الأولوية للسبق، ثم الردود، ثم المحتوى العام
        if self.task_scoop(): return
        
        # إذا لم يوجد سبق، اختر بين الرد أو النشر بنسبة 50/50 لتوزيع الضغط
        if random.random() > 0.5:
            if not self.task_reply():
                self.task_regular_post()
        else:
            if not self.task_regular_post():
                self.task_reply()

if __name__ == "__main__":
    bot = TechSupremeProfessional()
    bot.run_strategy()
