import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات الأساسية ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# معايير قياس الأداء (ROI)
ROI_WEIGHTS = {"like": 1.0, "repost": 2.5, "reply": 3.0, "poll_vote": 1.5}

# الرادار التقني (أخبار عالمية لتحويلها لممارسات فردية)
SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/category/gear/latest/rss"
]

# --- 2. توجيهات الذكاء الاصطناعي (Prompt) ---
PUBLISH_PROMPT = (
    "أنت خبير في الثورة الصناعية الرابعة (Industry 4.0) مخصص لتمكين (الأفراد). "
    "حوّل الخبر التقني التالي إلى ثريد تعليمي ودود باللهجة البيضاء: "
    "[TWEET_1] الفكرة: وش الجديد؟ وكيف هالأداة أو الجهاز بيفيدك (أنت) كفرد في يومك؟ "
    "[TWEET_2] الممارسة: خطوات عملية (Step-by-Step) لاستخدام هالتقنية لزيادة دخلك أو إنتاجيتك الشخصية. "
    "[POLL_QUESTION] سؤال استطلاع لقياس اهتمام الجمهور. "
    "[POLL_OPTIONS] خيارات قصيرة جداً (أقل من 20 حرف). "
    "القواعد: العربية، المصطلحات الإنجليزية بين قوسين، لا تقطع التغريدات، نبرة حماسية."
)

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS active_polls (tweet_id TEXT PRIMARY KEY, topic TEXT, expires_at TEXT, processed INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS roi_metrics (tweet_id TEXT PRIMARY KEY, topic TEXT, score REAL, created_at TEXT)")

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
            return r.choices[0].message.content
        except Exception as e:
            logging.error(f"❌ خطأ في توليد المحتوى: {e}")
            return None

    # --- 3. نظام النشر الذكي مع Retry Logic ---
    def _post_thread(self, text, link, topic):
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', text, re.S)
        last_id = None
        
        # تجهيز المهام (تغريدة 1، تغريدة 2، استطلاع)
        tasks = []
        if len(parts) >= 1:
            tasks.append({"text": f"1/ {parts[0].strip()}"[:280], "is_poll": False})
        if len(parts) >= 2:
            tasks.append({"text": f"2/ {parts[1].strip()}\n\n🔗 ممارسة: {link}"[:280], "is_poll": False})
        if len(parts) >= 4:
            options = [o.strip('- ').strip() for o in parts[3].strip().split('\n') if o.strip()][:4]
            tasks.append({"text": f"3/ {parts[2].strip()}"[:280], "is_poll": True, "options": options})

        for task in tasks:
            attempts = 0
            while attempts < 3:
                try:
                    if task["is_poll"]:
                        res = self.x.create_tweet(text=task["text"], in_reply_to_tweet_id=last_id, 
                                                 poll_options=task["options"], poll_duration_minutes=1440)
                        if res:
                            expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                            with sqlite3.connect(DB_FILE) as conn:
                                conn.execute("INSERT INTO active_polls VALUES (?, ?, ?, 0)", (res.data["id"], topic, expires))
                    else:
                        res = self.x.create_tweet(text=task["text"], in_reply_to_tweet_id=last_id)
                    
                    if res:
                        last_id = res.data["id"]
                        logging.info("✅ تم نشر جزء من الثريد. انتظار 60 ثانية للأمان...")
                        time.sleep(60) 
                        break 
                
                except tweepy.TooManyRequests:
                    attempts += 1
                    wait_time = attempts * 300 # 5 دقائق، ثم 10 دقائق
                    logging.warning(f"⚠️ خطأ 429 (تجاوز الحدود). انتظار {wait_time/60} دقيقة...")
                    time.sleep(wait_time)
                except Exception as e:
                    logging.error(f"❌ فشل النشر: {e}")
                    return

    def run_cycle(self):
        logging.info("🚀 بدء الدورة التشغيلية: فحص المصادر...")
        for url in SOURCES:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue
                
                content = self._generate_ai(PUBLISH_PROMPT, e.title, h)
                if content:
                    # حفظ في الذاكرة أولاً لمنع التكرار في حال فشل النشر
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                    
                    self._post_thread(content, e.link, e.title)
                    logging.info("🏁 تمت الدورة بنجاح.")
                    return 

if __name__ == "__main__":
    TechSupremeSystem().run_cycle()
