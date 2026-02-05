import os, sqlite3, logging, hashlib, time, random
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والذاكرة ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. المجالات الستة المستهدفة (تركيز الأفراد) ---
TARGET_TOPICS = [
    "الذكاء الاصطناعي للأفراد (ChatGPT, MidJourney, DALL·E, Grok Imagine) واستخداماته الإبداعية",
    "الهواتف والأجهزة الذكية (Apple, Samsung, Xiaomi) والمقارنات والحيل التقنية",
    "الألعاب الإلكترونية وتقنيات الواقع المعزز (VR/AR) والترفيه الرقمي",
    "التطبيقات العملية لإدارة الوقت، الصحة، وتعديل الفيديو والتصوير",
    "الأمن الرقمي الشخصي، حماية الخصوصية، وتأمين الحسابات من الاختراقات",
    "التحديات والمسابقات التقنية، ألغاز AI، وتحديات البرمجة"
]

# مصادر السبق الصحفي
SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://www.technologyreview.com/feed/",
    "https://www.engadget.com/rss.xml"
]

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 25  # حصة الحساب المدفوع
        try:
            me = self.x.get_me()
            self.my_user_id = str(me.data.id)
            logging.info(f"✅ تم التعرف على البوت ID: {self.my_user_id}")
        except: 
            self.my_user_id = None
            logging.warning("⚠️ لم يتم التعرف على ID الحساب.")

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory ON memory(h)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history ON tweet_history(tweet_id)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        if self.ai_calls >= self.MAX_AI_CALLS: return None
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": sys_p + " قيد: العربية، مصطلحات إنجليزية (بين قوسين)، لا هلوسة، حقائق فقط، نقاط مركزة، ذكر الأداة بدقة."},
                    {"role": "user", "content": user_p}
                ],
                temperature=0.2
            )
            return r.choices[0].message.content
        except Exception as e:
            logging.error(f"❌ AI Error: {e}"); return None

    # --- محرك السبق الصحفي المتخصص في المجالات الستة ---
    def check_for_scoops(self):
        logging.info("🕵️ فحص الأخبار العاجلة في المجالات الستة...")
        for url in SOURCES:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            latest = feed.entries[0]
            h = hashlib.sha256(latest.title.encode()).hexdigest()
            
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

            # التحقق من صلة الخبر بالمجالات الستة
            validation = self._safe_ai_call("أنت مصفّي أخبار عالي الدقة.", 
                f"هل يخص هذا الخبر [{latest.title}] (AI للأفراد، هواتف، ألعاب، تطبيقات، أمن رقمي، مسابقات)؟ أجب بـ نعم/لا فقط.")
            
            if validation and "نعم" in validation:
                content = self._safe_ai_call("🚨 سبق تقني عاجل:", 
                    f"حلل هذا الخبر [{latest.title}] واكتبه في نقاط مركزة تشرح الفائدة للفرد مع ذكر الأداة/الشركة.")
                if content:
                    self._publish_thread(content, "🚨 سبق تقني عاجل:")
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                    return True
        return False

    # --- نظام الردود الذكية ---
    def process_smart_replies(self):
        logging.info("🔍 فحص التفاعلات...")
        query = "(\"كيف أستخدم AI\" OR #عمان_تتقدم OR \"أفضل هاتف\" OR \"اختراق\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=10, user_auth=True)
            if not tweets or not tweets.data: return
            for t in tweets.data[:3]:
                if str(t.author_id) == self.my_user_id: continue
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=?", (str(t.id),)).fetchone(): continue
                
                reply = self._safe_ai_call("خبير تقني 4.0 ودود.", f"رد بنصيحة عملية ونقاط مركزة على: {t.text}")
                if reply:
                    self.x.create_tweet(text=f"{reply[:280]}", in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO tweet_history VALUES (?, ?)", (str(t.id), datetime.now().isoformat()))
                    time.sleep(5)
        except Exception as e: logging.error(f"❌ خطأ في الردود: {e}")

    # --- محرك السلاسل Threads ---
    def _publish_thread(self, content, prefix="💡 تجربة تقنية:\n"):
        chunks = [content[i:i+250] for i in range(0, len(content), 250)]
        prev_id = None
        for i, chunk in enumerate(chunks):
            text = f"{prefix if i==0 else ''}{chunk}"
            tweet = self.x.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
            prev_id = tweet.data['id']
            time.sleep(2)

    def execute_scheduled_flow(self):
        # مسابقة الخميس
        if datetime.now().weekday() == 3:
            quiz = self._safe_ai_call("🧠 صغ تحدي تقني للأفراد بنقاط مركزة.", "تحدي الأسبوع")
            if quiz: self._publish_thread(quiz, "🧩 تحدي الأسبوع:\n")
            return

        # محتوى استراتيجي اعتيادي
        topic = random.choice(TARGET_TOPICS)
        content = self._safe_ai_call(f"صغ ممارسة إبداعية للفرد في {topic} بنقاط مركزة.", "ممارسة اليوم")
        if content: self._publish_thread(content)

    def run(self):
        if not self.check_for_scoops():
            self.process_smart_replies()
            time.sleep(10)
            self.execute_scheduled_flow()

if __name__ == "__main__":
    bot = TechSupremeSystem()
    while True:
        bot.run()
        time.sleep(1800) # فحص كل 30 دقيقة
