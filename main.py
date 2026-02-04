import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlparse

# 1. إعدادات البيئة والمصادر (Environment & Elite Sources)
load_dotenv()
DB_FILE = "news_master_2026.db"
LOG_FILE = "system_master.log"

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default", "https://krebsonsecurity.com/feed/"],
    "FinTech_Crypto": ["https://www.coindesk.com/arc/outboundfeeds/rss/"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"]
}

# 2. القائمة البيضاء للهاشتاغات (نخبوية وموثوقة 100%)
APPROVED_HASHTAGS = {
    "AI_Official": ["#الذكاء_الاصطناعي", "#AI", "#TechNews"],
    "CyberSecurity": ["#الأمن_السيبراني", "#CyberSecurity"],
    "FinTech_Crypto": ["#التقنية_المالية", "#FinTech"],
    "Microsoft_Official": ["#مايكروسوفت", "#أسرار_التقنية"],
    "Education": ["#سلسلة_جوجل", "#تعلم_الذكاء_الاصطناعي"],
    "Challenge": ["#مسابقة_TechElite", "#تحدي_الأسبوع"]
}

# 3. الحسابات المستهدفة للردود (أرباح الـ 0.2 سنت)
TARGET_ACCOUNTS = ["GoogleAI", "OpenAI", "Microsoft", "elonmusk", "ylecun", "satyanadella"]

STRICT_SYSTEM_PROMPT = """
أنت رئيس تحرير تقني (TechElite). صُغ محتوى احترافياً بناءً على المصادر الرسمية.
القواعد:
1. مثلث القيمة: [TWEET_1] خُطّاف، [TWEET_2] جوهر المعلومة (مصطلح إنجليزي بين قوسين)، [POLL_QUESTION] سؤال استطلاع، [POLL_OPTIONS] خيارات (-).
2. المسابقات: صُغ لغزاً تقنياً للمحترفين حول MS 365 أو AI.
3. الردود: ردود ذكية، تحليلية، قصيرة، وتضيف قيمة.
4. ممنوع الهاشتاغات (#) داخل النص نهائياً.
"""

class TechEliteUltimate2026:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.max_daily = 4

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    hash TEXT PRIMARY KEY, title TEXT, category TEXT, 
                    keywords TEXT, published_at TEXT, poll_id TEXT
                )
            """)

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _clean_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def _generate_ai(self, prompt, sys_mod=""):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": STRICT_SYSTEM_PROMPT + sys_mod}, {"role": "user", "content": prompt}],
                temperature=0.2
            )
            return r.choices[0].message.content.strip()
        except: return None

    # --- [1] دالة الردود الذكية لرفع الأرباح ---
    def engage_smart_replies(self):
        for account in TARGET_ACCOUNTS:
            try:
                user = self.x_client.get_user(username=account)
                tweets = self.x_client.get_users_tweets(id=user.data.id, max_results=5, exclude=['retweets', 'replies'])
                if not tweets.data: continue
                latest = tweets.data[0]
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM news WHERE poll_id=?", (f"reply_{latest.id}",)).fetchone(): continue
                
                reply = self._generate_ai(f"رد تقني ذكي على: {latest.text}")
                if reply:
                    time.sleep(random.randint(120, 240)) # أمان لسياسات أكس
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=latest.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO news (hash, poll_id, published_at) VALUES (?, ?, ?)", 
                                     (str(latest.id), f"reply_{latest.id}", datetime.now().isoformat()))
                    logging.info(f"✅ تم الرد الذكي على {account}")
                    break 
            except: continue

    # --- [2] دالة تحليل الاستطلاعات ---
    def analyze_yesterday_poll(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        with sqlite3.connect(DB_FILE) as conn:
            row = conn.execute("SELECT poll_id, title FROM news WHERE published_at LIKE ? AND poll_id IS NOT NULL", (f"{yesterday}%",)).fetchone()
            if not row: return
            try:
                tweet = self.x_client.get_tweet(id=row[0], expansions="attachments.poll_ids")
                poll = tweet.includes['polls'][0]
                results = "\n".join([f"- {opt['label']}: {opt['votes']} صوت" for opt in poll['options']])
                analysis = self._generate_ai(f"حلل منطقياً نتائج هذا الاستطلاع: {results}")
                self.x_client.create_tweet(text=f"📊 تحليل استطلاع الأمس: {row[1]}\n\n{results}\n\n💡 التحليل المنطقي:\n{analysis[:180]}\n#نتائج_TechElite")
            except: pass

    # --- [3] دالة النشر العام (ثريد + استطلاع) ---
    def post_thread(self, ai_text, url, title, cat):
        clean_url = self._clean_url(url)
        clean_text = re.sub(r'#\w+', '', ai_text).strip()
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', clean_text, re.S)
        if len(parts) < 3: return False
        
        tags = " ".join(random.sample(APPROVED_HASHTAGS.get(cat, ["#تقنية"]), 2))
        last_id, poll_id = None, None
        
        for i, content in enumerate(parts[:3]):
            msg = f"{i+1}/ {content.strip()}"
            if i == 1: msg += f"\n\n🔗 المصدر:\n{clean_url}"
            if i == 2: msg += f"\n\n{tags}"
            
            try:
                if i == 2 and len(parts) >= 4:
                    opts = [o.strip() for o in parts[3].split('-') if o.strip()][:4]
                    res = self.x_client.create_tweet(text=msg[:280], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                    poll_id = res.data["id"]
                else:
                    res = self.x_client.create_tweet(text=msg[:280], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]; time.sleep(85)
            except: break
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO news (hash, title, category, published_at, poll_id) VALUES (?, ?, ?, ?, ?)", 
                         (hashlib.sha256(title.encode()).hexdigest(), title, cat, datetime.now().isoformat(), poll_id))
        return True

    # --- [4] دورة التشغيل الذكية ---
    def run_cycle(self):
        day = datetime.now().strftime('%A')
        self.analyze_yesterday_poll()
        self.engage_smart_replies()
        
        published = 0
        # الخميس: المسابقة الأسبوعية
        if day == "Thursday":
            q = self._generate_ai("صُغ مسابقة تقنية قوية ليوم الخميس.", "\nركز على تحديات Microsoft 365.")
            if q and self.post_thread(q, "https://microsoft.com", "تحدي الخميس التقني", "Challenge"):
                published += 1

        # الأربعاء: سلسلة جوجل AI
        if day == "Wednesday":
            ai_q = self._generate_ai("ثريد عن ميزة خفية في Google Gemini.")
            if ai_q and self.post_thread(ai_q, "https://ai.google", "سلسلة جوجل AI", "Education"):
                published += 1

        # النشر اليومي
        cats = list(SOURCES.keys()); random.shuffle(cats)
        for c in cats:
            if published >= self.max_daily: break
            feed = feedparser.parse(SOURCES[c][0])
            for e in feed.entries[:3]:
                if published >= self.max_daily: break
                h = hashlib.sha256(e.title.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone(): continue
                
                txt = self._generate_ai(f"الموضوع: {e.title}\n{getattr(e, 'summary', '')}")
                if txt and self.post_thread(txt, e.link, e.title, c):
                    published += 1; break

if __name__ == "__main__":
    TechEliteUltimate2026().run_cycle()
