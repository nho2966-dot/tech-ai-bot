import os, sqlite3, logging, hashlib, time, re
from datetime import datetime, timezone, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# مصادر الأخبار وكلمات بحث الردود
SOURCES = ["https://www.theverge.com/rss/index.xml", "https://venturebeat.com/category/ai/feed/"]
REPLY_QUERIES = "(\"أداة ذكاء اصطناعي\" OR \"كيف استخدم AI\" OR \"تطوير مهارات تقنية\") -is:retweet"

# --- 2. توجيهات الذكاء الاصطناعي ---
PUBLISH_PROMPT = "أنت خبير في الثورة الصناعية الرابعة لتمكين الأفراد. صُغ ثريداً: [TWEET_1] الفكرة والجدوى للفرد، [TWEET_2] ممارسة عملية (Step-by-Step)، [POLL_QUESTION] سؤال استطلاع، [POLL_OPTIONS] خيارات قصيرة. العربية، مصطلحات إنجليزية بين قوسين."
REPLY_PROMPT = "أنت صديق تقني خبير. رد على الاستفسار بأسلوب (How-to) عملي وبسيط جداً، اقترح أداة أو ممارسة تقنية تفيد السائل فوراً."

class TechSupremeSystem:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS active_polls (tweet_id TEXT PRIMARY KEY, topic TEXT, expires_at TEXT, processed INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (user_id TEXT PRIMARY KEY, dt TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # --- نظام المحاولة المتكررة (Retry Logic) ---
    def _safe_x_call(self, func, **kwargs):
        attempts = 0
        while attempts < 3:
            try:
                return func(**kwargs)
            except tweepy.TooManyRequests:
                attempts += 1
                wait = attempts * 300
                logging.warning(f"⚠️ خطأ 429! انتظار {wait/60} دقيقة...")
                time.sleep(wait)
            except Exception as e:
                logging.error(f"❌ خطأ X: {e}")
                return None
        return None

    def _generate_ai(self, sys_p, user_p):
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct", 
                messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]
            )
            return r.choices[0].message.content
        except: return None

    # --- 3. تنفيذ الردود الذكية ---
    def process_smart_replies(self):
        logging.info("🔍 البحث عن استفسارات للرد عليها...")
        tweets = self._safe_x_call(self.x.search_recent_tweets, query=REPLY_QUERIES, max_results=10, user_auth=True)
        
        if tweets and tweets.data:
            for t in tweets.data:
                # التأكد من عدم الرد على نفس الشخص مرتين في يوم واحد
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM replies WHERE user_id=? AND dt > ?", 
                                    (str(t.author_id), (datetime.now() - timedelta(days=1)).isoformat())).fetchone():
                        continue

                reply_text = self._generate_ai(REPLY_PROMPT, t.text)
                if reply_text:
                    if self._safe_x_call(self.x.create_tweet, text=reply_text[:280], in_reply_to_tweet_id=t.id):
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT OR REPLACE INTO replies VALUES (?, ?)", (str(t.author_id), datetime.now().isoformat()))
                        logging.info(f"✅ تم الرد على المستخدم: {t.author_id}")
                        time.sleep(60)

    # --- 4. تنفيذ النشر (ثريد + استطلاع) ---
    def execute_publishing(self):
        for url in SOURCES:
            feed = feedparser.parse(url)
            for e in feed.entries[:3]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

                content = self._generate_ai(PUBLISH_PROMPT, e.title)
                if content:
                    self._post_thread(content, e.link, e.title, h)
                    return

    def _post_thread(self, text, link, topic, h):
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', text, re.S)
        last_id = None
        
        # مهمة 1: الفكرة
        res = self._safe_x_call(self.x.create_tweet, text=f"1/ {parts[0].strip()}"[:280])
        if res: last_id = res.data["id"]
        time.sleep(60)

        # مهمة 2: الممارسة + الرابط
        if len(parts) > 1 and last_id:
            msg = f"2/ {parts[1].strip()}\n\n🔗 ممارسة: {link}"
            res = self._safe_x_call(self.x.create_tweet, text=msg[:280], in_reply_to_tweet_id=last_id)
            if res: last_id = res.data["id"]
            time.sleep(60)

        # مهمة 3: الاستطلاع
        if len(parts) > 3 and last_id:
            options = [o.strip('- ').strip() for o in parts[3].strip().split('\n') if o.strip()][:4]
            res = self._safe_x_call(self.x.create_tweet, text=f"3/ {parts[2].strip()}", 
                                    in_reply_to_tweet_id=last_id, poll_options=options, poll_duration_minutes=1440)
            if res:
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO active_polls VALUES (?, ?, ?, 0)", (res.data["id"], topic, (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()))

        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))

    def run_all(self):
        self.process_smart_replies() # أولاً التفاعل مع الجمهور
        self.execute_publishing()     # ثانياً نشر محتوى جديد

if __name__ == "__main__":
    TechSupremeSystem().run_all()
