import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات الأساسية ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. توجيهات الذكاء الاصطناعي (Prompts) ---
SYSTEM_REPLY_PROMPT = (
    "أنت خبير تقني ودود ومختصر. رد على الاستفسار بممارسة عملية (Industry 4.0 Practice) "
    "تفيد الفرد فوراً. استخدم العربية، وضع المصطلحات الإنجليزية بين قوسين، ولا تتجاوز 280 حرف."
)

SYSTEM_THREAD_PROMPT = (
    "أنت خبير في الثورة الصناعية الرابعة للأفراد. صُغ تغريدة تعليمية مركزة: "
    "ابدأ بـ [الفكرة] ثم [الممارسة العملية]. "
    "القواعد: العربية، المصطلحات الإنجليزية بين قوسين، نبرة حماسية."
)

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        # 🎯 Rate-Limit Guard لمنع تعليق GitHub Actions
        self.ai_calls = 0
        self.MAX_AI_CALLS = 3 

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
            logging.warning("⛔ تم بلوغ حد AI المسموح به في هذه الدورة.")
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

    # --- 3. محرك الردود الذكية (إصلاح خطأ 400) ---
    def process_smart_replies(self):
        logging.info("🔍 فحص استفسارات الجمهور...")
        # الحد الأدنى لـ max_results في تويتر هو 10
        query = "(\"كيف أستخدم AI\" OR \"أداة ذكاء اصطناعي\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=10, user_auth=True)
            if not tweets or not tweets.data: return

            for t in tweets.data:
                if self.ai_calls >= self.MAX_AI_CALLS: break
                
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM replies WHERE user_id=?", (str(t.author_id),)).fetchone():
                        continue

                reply_txt = self._safe_ai_call(SYSTEM_REPLY_PROMPT, t.text)
                if reply_txt:
                    try:
                        self.x.create_tweet(text=reply_txt[:280], in_reply_to_tweet_id=t.id)
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT INTO replies VALUES (?, ?)", (str(t.author_id), datetime.now().isoformat()))
                            conn.commit()
                        logging.info(f"✅ تم الرد على: {t.author_id}")
                        break # رد واحد ذكي في كل ساعة كافٍ جداً للأمان
                    except Exception as e:
                        logging.error(f"❌ فشل إرسال الرد: {e}")
                        break
        except Exception as e:
            logging.error(f"❌ خطأ في البحث: {e}")

    # --- 4. محرك النشر (إصلاح خطأ 429) ---
    def execute_publishing(self):
        if self.ai_calls >= self.MAX_AI_CALLS: return
        logging.info("🌍 فحص الأخبار الجديدة...")
        feed = feedparser.parse("https://www.theverge.com/rss/index.xml")
        
        for e in feed.entries[:5]:
            h = hashlib.sha256(e.title.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

            content = self._safe_ai_call(SYSTEM_THREAD_PROMPT, e.title)
            if content:
                try:
                    # نشر تغريدة واحدة قوية لتجنب الـ Rate Limit
                    tweet_text = f"📌 {e.title}\n\n{content[:240]}"
                    res = self.x.create_tweet(text=tweet_text)
                    if res:
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                            conn.commit()
                        logging.info(f"✅ تم نشر الخبر: {e.title}")
                        return # الخروج بعد أول نجاح
                except Exception as ex:
                    logging.error(f"❌ فشل النشر: {ex}")
                    return 

    def run(self):
        logging.info("🚀 بدء دورة التشغيل المحدثة...")
        self.process_smart_replies() 
        self.execute_publishing()     
        logging.info("🏁 انتهت الدورة بنجاح.")

if __name__ == "__main__":
    TechSupremeSystem().run()
