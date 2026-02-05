import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والتحصين ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. توجيهات الذكاء الاصطناعي (Prompts) ---
# ردود ذكية تركز على ممارسات الثورة 4.0 للأفراد
SYSTEM_REPLY_PROMPT = (
    "أنت خبير تقني ودود ومختصر (Peer Expert). رد على الاستفسار بممارسة عملية (Industry 4.0 Practice) "
    "تفيد الفرد فوراً في إنتاجيته أو دخله. استخدم العربية، وضع المصطلحات الإنجليزية بين قوسين، ولا تتجاوز 280 حرف."
)

# نشر محتوى جديد (ثريد تعليمي)
SYSTEM_THREAD_PROMPT = (
    "أنت خبير في الثورة الصناعية الرابعة للأفراد. صُغ ثريداً تعليمياً من جزأين: "
    "[TWEET_1] الفكرة: وش الجديد؟ وكيف هالأداة بتفيدك (أنت) كفرد في يومك؟ "
    "[TWEET_2] الممارسة: خطوات عملية (Step-by-Step) لاستخدام هالتقنية. "
    "القواعد: العربية، المصطلحات الإنجليزية بين قوسين، نبرة حماسية."
)

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # 🎯 Rate-Limit Guard: منع الـ GitHub Actions من التعليق
        self.ai_calls = 0
        self.MAX_AI_CALLS = 3 # حد أقصى لطلبات AI في كل Run

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (user_id TEXT PRIMARY KEY, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        if self.ai_calls >= self.MAX_AI_CALLS:
            logging.warning("⛔ تم بلوغ الحد الأقصى لطلبات AI. التوقف ذكاءً.")
            return None
        try:
            self.ai_calls += 1
            logging.info(f"🤖 طلب AI رقم {self.ai_calls}...")
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]
            )
            return r.choices[0].message.content
        except Exception as e:
            logging.error(f"❌ خطأ AI: {e}")
            return None

    # --- 3. محرك الردود الذكية (Replying) ---
    def process_smart_replies(self):
        logging.info("🔍 فحص استفسارات الجمهور للرد عليها...")
        # كلمات البحث المستهدفة
        query = "(\"أداة ذكاء اصطناعي\" OR \"كيف أستخدم AI\" OR \"تعلم البرمجة\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=5, user_auth=True)
            if not tweets or not tweets.data: return

            for t in tweets.data:
                if self.ai_calls >= self.MAX_AI_CALLS: break
                
                # فحص الذاكرة: لا نرد على نفس الشخص مرتين في 24 ساعة
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM replies WHERE user_id=?", (str(t.author_id),)).fetchone():
                        continue

                reply_txt = self._safe_ai_call(SYSTEM_REPLY_PROMPT, t.text)
                if reply_txt:
                    self.x.create_tweet(text=reply_txt[:280], in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO replies VALUES (?, ?)", (str(t.author_id), datetime.now().isoformat()))
                    logging.info(f"✅ تم الرد على: {t.author_id}")
                    time.sleep(2) 
        except Exception as e:
            logging.error(f"❌ خطأ في الردود: {e}")

    # --- 4. محرك النشر (Publishing) ---
    def execute_publishing(self):
        if self.ai_calls >= self.MAX_AI_CALLS: return
        logging.info("🌍 فحص الأخبار الجديدة للنشر...")
        feed = feedparser.parse("https://www.theverge.com/rss/index.xml")
        
        for e in feed.entries[:3]:
            h = hashlib.sha256(e.title.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

            content = self._safe_ai_call(SYSTEM_THREAD_PROMPT, e.title)
            if content:
                try:
                    # تقسيم ونشر ثريد مبسط
                    parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', content, re.S)
                    t1 = f"📌 {e.title}\n\n{parts[0].strip()}" if parts else content
                    res = self.x.create_tweet(text=t1[:280])
                    
                    if res and len(parts) > 1:
                        self.x.create_tweet(text=parts[1].strip()[:280], in_reply_to_tweet_id=res.data['id'])
                    
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                    logging.info(f"✅ تم نشر محتوى جديد: {e.title}")
                    break
                except Exception as ex:
                    logging.error(f"❌ فشل النشر: {ex}")

    def run(self):
        logging.info("🚀 بدء الدورة الشاملة...")
        self.process_smart_replies() # تفاعل أولاً
        self.execute_publishing()     # انشر ثانياً
        logging.info("🏁 انتهت الدورة.")

if __name__ == "__main__":
    TechSupremeSystem().run()
