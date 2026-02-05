import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والتحصين ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# أوزان قياس الأداء (ROI)
ROI_WEIGHTS = {"like": 1.0, "repost": 2.5, "reply": 3.0, "poll_vote": 1.5}

# المصادر (تركيز: AI + أجهزة + ممارسات الثورة 4.0)
SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/category/gear/latest/rss"
]

# --- 2. البرومبتس (الودودة والعملية) ---
PUBLISH_PROMPT = (
    "أنت خبير في الثورة الصناعية الرابعة (Industry 4.0) تركز على تمكين الأفراد. "
    "صُغ ثريداً ودياً باللهجة البيضاء: "
    "[TWEET_1] الفكرة: وش الجديد؟ وكيف هالأداة أو الجهاز بيفيد (أنت) كفرد في يومك؟ "
    "[TWEET_2] الممارسة: خطوات عملية لاستخدام هالتقنية لزيادة دخلك أو إنتاجيتك (AI Practice). "
    "[POLL_QUESTION] سؤال استطلاع ودي لقياس اهتمام الجمهور. "
    "[POLL_OPTIONS] خيارات قصيرة جداً (أقل من 20 حرف). "
    "القواعد: العربية، المصطلحات الإنجليزية بين قوسين، لا تقطع التغريدات."
)

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS active_polls (tweet_id TEXT PRIMARY KEY, topic TEXT, expires_at TEXT, processed INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS roi_metrics (tweet_id TEXT PRIMARY KEY, topic TEXT, content_type TEXT, score REAL, created_at TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _generate_ai(self, sys_p, user_p, h):
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct", 
                messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}], 
                temperature=0.7
            )
            content = r.choices[0].message.content
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
            return content
        except Exception as e:
            logging.error(f"❌ خطأ AI: {e}")
            return None

    def _post_thread(self, text, link, topic):
        # تقسيم المحتوى بناءً على الأوسمة
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', text, re.S)
        last_id = None
        
        try:
            # 1. التغريدة الأولى (الفكرة)
            if len(parts) > 0:
                res = self.x.create_tweet(text=f"1/ {parts[0].strip()}"[:280])
                last_id = res.data["id"]
                time.sleep(10)

            # 2. التغريدة الثانية (الممارسة + الرابط)
            if len(parts) > 1 and last_id:
                msg = f"2/ {parts[1].strip()}\n\n🔗 ممارسة عملية: {link}"
                res = self.x.create_tweet(text=msg[:280], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(10)

            # 3. التغريدة الثالثة (الاستطلاع الحقيقي)
            if len(parts) > 3 and last_id:
                poll_q = parts[2].strip()[:280]
                options = [o.strip('- ').strip() for o in parts[3].strip().split('\n') if o.strip()][:4]
                if len(options) >= 2:
                    res = self.x.create_tweet(
                        text=f"3/ {poll_q}",
                        in_reply_to_tweet_id=last_id,
                        poll_options=options,
                        poll_duration_minutes=1440
                    )
                    # حفظ الاستطلاع للمتابعة
                    expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO active_polls VALUES (?, ?, ?, 0)", (res.data["id"], topic, expires))
            
            logging.info(f"✅ تم نشر الثريد بنجاح عن: {topic}")
        except Exception as e:
            logging.error(f"❌ خطأ أثناء النشر: {e}")

    def run_cycle(self):
        logging.info("🚀 تشغيل يدوي: جاري فحص الرادار التقني...")
        
        for url in SOURCES:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue
                
                # توليد ونشر أول خبر جديد يجده الرادار
                content = self._generate_ai(PUBLISH_PROMPT, e.title, h)
                if content:
                    self._post_thread(content, e.link, e.title)
                    return # إنهاء الدورة بعد نشر واحد لضمان الجودة

if __name__ == "__main__":
    TechSupremeSystem().run_cycle()
