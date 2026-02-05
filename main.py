import os, sqlite3, logging, hashlib, time, random
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

# --- المصادر الاستراتيجية للسبق الصحفي ---
BREAKING_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://www.technologyreview.com/feed/"
]

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.MAX_AI_CALLS = 18 # رفع الحصة لدعم الأخبار العاجلة
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
                messages=[{"role": "system", "content": sys_p + " قيد: لا هلوسة، حقائق فقط."}, {"role": "user", "content": user_p}],
                temperature=0.2
            )
            return r.choices[0].message.content
        except Exception as e:
            logging.error(f"❌ AI Error: {e}"); return None

    # --- محرك السبق الصحفي (Breaking News) ---
    def check_for_scoop(self):
        logging.info("🕵️ جاري البحث عن سبق صحفي تقني...")
        for url in BREAKING_SOURCES:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            
            # نأخذ أول خبر فقط (الأحدث على الإطلاق)
            latest = feed.entries[0]
            h = hashlib.sha256(latest.title.encode()).hexdigest()
            
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

            # صياغة السبق الصحفي مع ربطه بممارسات الثورة 4.0
            prompt = f"هذا خبر عاجل: [{latest.title}]. صغ تغريدة 'سبق صحفي' تشرح ممارسته العملية للفرد فوراً. ابدأ بـ 🚨 سبق تقني:"
            content = self._safe_ai_call("أنت مراسل تقني خبير ودقيق.", prompt)
            
            if content:
                self.x.create_tweet(text=f"{content[:250]} #عمان_تتقدم #سبق_تقني")
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                    conn.commit()
                logging.info("🚨 تم نشر سبق صحفي جديد!")
                return True # توقف بعد نشر السبق
        return False

    # --- المنطق الأسبوعي (المسابقة والاستطلاع) ---
    def execute_strategic_flow(self):
        # 1. التحقق من السبق الصحفي أولاً
        if self.check_for_scoop(): return

        # 2. إذا لم يوجد سبق، ننتقل للجدول المعتاد
        now = datetime.now()
        day_of_week = now.weekday() # 3 هو الخميس

        if day_of_week == 3: # الخميس: يوم المسابقة
            content = self._safe_ai_call("صغ مسابقة تقنية أسبوعية عن ممارسات الذكاء الاصطناعي.", "تحدي الأسبوع")
            if content: self.x.create_tweet(text=f"🏆 مسابقة الأسبوع:\n{content[:260]}")
        else:
            # نشر اعتيادي أو استطلاع ذكي
            topic = random.choice(["AI", "3D Printing", "IoT", "Smart Devices"])
            content = self._safe_ai_call(f"صغ ممارسة عملية في {topic}.", "خبر تقني جديد")
            if content:
                # قرار الاستطلاع الذكي
                if "مستقبل" in content or "تفضيل" in content:
                    self.x.create_tweet(text=f"📊 استطلاع تقني:\n{content[:240]}")
                else:
                    self.x.create_tweet(text=f"📌 ممارسة اليوم:\n{content[:270]}")

    def run(self):
        # تنفيذ الردود الذكية أولاً (بدون تكرار وبدون الرد على النفس)
        self.process_smart_replies() # (تم شرح تفاصيلها في الرد السابق)
        time.sleep(20)
        self.execute_strategic_flow()

if __name__ == "__main__":
    TechSupremeSystem().run()
