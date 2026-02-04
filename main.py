import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from tweepy.errors import TooManyRequests

# تحميل الإعدادات
load_dotenv()
DB_FILE = "news_master_2026.db"
LOG_FILE = "system_master.log"

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

# 1. المصادر الرسمية النخبوية (Elite Official Sources)
SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default", "https://krebsonsecurity.com/feed/"],
    "FinTech_Crypto": ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://www.theblock.co/rss.xml"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"],
    "Tech_Authority": ["https://arstechnica.com/feed/", "https://www.wired.com/feed/rss"]
}

# 2. المرجع المعرفي والقواعد التحريرية
KNOWLEDGE_BASE = {
    "microsoft": "خبايا Microsoft 365، اختصارات الإنتاجية، ميزات Windows 11.",
    "x_profit": "أرباح الردود (0.2 سنت)، قوة الحسابات الموثقة، قاعدة آخر 20 منشور.",
    "google_ai": "سلسلة أسبوعية دورية تشرح أدوات جوجل للذكاء الاصطناعي باحترافية."
}

STRICT_SYSTEM_PROMPT = f"""
أنت رئيس تحرير (TechElite). صُغ محتوى تقنياً احترافياً جداً بناءً على المصادر الرسمية فقط.
المراجع المعتمدة: {KNOWLEDGE_BASE}
القواعد القطعية:
1. نوع العرض بين (خبر عاجل، ثريد تعليمي، قائمة نصائح، تحذير أمني).
2. مثلث القيمة: [TWEET_1] خُطّاف جذاب، [TWEET_2] جوهر السر التقني، [POLL_QUESTION] تفاعل المتابعين.
3. العربية ودودة ورصينة، مع مصطلحات إنجليزية بين قوسين (Term).
4. توليد 3 هاشتاغات ديناميكية ذكية في نهاية الثريد.
5. منع الرموز الصينية أو HTML تماماً.
"""

class TechEliteIntegrated2026:
    def __init__(self):
        self.max_daily = 4
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    hash TEXT PRIMARY KEY, title TEXT, category TEXT, 
                    keywords TEXT, hashtags TEXT, published_at TEXT
                )
            """)

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _extract_semantic_keywords(self, title, summary):
        """تحليل دلالي للعنوان والملخص لمنع التكرار"""
        combined = f"{title} {summary}".lower()
        words = re.findall(r'\w+', combined)
        stop_words = {'the', 'with', 'update', 'launch', 'official', 'google', 'microsoft', 'tech'}
        important = [w for w in words if len(w) > 3 and w not in stop_words]
        return ",".join(list(set(important))[:8])

    def _is_duplicate_semantic(self, new_keywords):
        """التحقق من تكرار الموضوع دلالياً خلال 48 ساعة"""
        if not new_keywords: return False
        with sqlite3.connect(DB_FILE) as conn:
            limit_date = (datetime.now() - timedelta(days=2)).isoformat()
            cursor = conn.execute("SELECT keywords FROM news WHERE published_at > ?", (limit_date,))
            new_set = set(new_keywords.split(','))
            for row in cursor.fetchall():
                if not row[0]: continue
                existing_set = set(row[0].split(','))
                if len(new_set.intersection(existing_set)) >= 4: return True
        return False

    def post_thread_with_retry(self, ai_text, url, title, cat, keywords):
        """نظام النشر مع Retry & Backoff ذكي"""
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', ai_text, re.S)
        if len(parts) < 3: return False
        hashtags = " ".join(re.findall(r'#\w+', ai_text))
        last_id = None
        
        for i, content in enumerate(parts[:3]):
            text = f"{i+1}/ {content.strip()}"
            if i == 1: text += f"\n\n🔗 المصدر الرسمي: {url}"
            
            for attempt in range(3):
                try:
                    if i == 2 and len(parts) >= 4:
                        opts = [o.strip() for o in parts[3].split('-') if o.strip()][:4]
                        res = self.x_client.create_tweet(text=text[:280], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                    else:
                        res = self.x_client.create_tweet(text=text[:280], in_reply_to_tweet_id=last_id)
                    last_id = res.data["id"]
                    time.sleep(75)
                    break
                except TooManyRequests as e:
                    wait = int(e.response.headers.get('Retry-After', 300))
                    time.sleep(wait)
                except Exception as e:
                    logging.error(f"❌ خطأ محاولة {attempt+1}: {e}")
                    time.sleep(30 * (attempt + 1))
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO news VALUES (?, ?, ?, ?, ?, ?)", 
                         (hashlib.sha256(title.encode()).hexdigest(), title, cat, keywords, hashtags, datetime.now().isoformat()))
        return True

    def post_weekly_report(self):
        """نشر تقرير أداء أسبوعي للمتابعين تلقائياً"""
        with sqlite3.connect(DB_FILE) as conn:
            last_week = (datetime.now() - timedelta(days=7)).isoformat()
            data = conn.execute("SELECT category, COUNT(*) FROM news WHERE published_at > ? GROUP BY category", (last_week,)).fetchall()
            if not data: return
            
            report = "📊 حصاد الأسبوع التقني في TechElite:\n\n"
            for cat, count in data: report += f"🔹 {cat}: {count} تغريدة\n"
            report += "\nنقدم لكم الحقائق من مصادرها الرسمية. #Tech_Report #AI"
            self.x_client.create_tweet(text=report)

    def run_cycle(self):
        published_count = 0
        current_day = datetime.now().strftime('%A')
        
        # السبت: التقرير الأسبوعي
        if current_day == "Saturday": self.post_weekly_report()

        # الأربعاء: سلسلة جوجل AI
        if current_day == "Wednesday":
            ai_text = self._generate_ai("سلسلة الأسبوع: أداة Google AI الرسمية وكيفية استغلالها احترافياً.")
            if ai_text and self.post_thread_with_retry(ai_text, "https://ai.google/", "Google AI Series", "Education", "google,ai,official"):
                published_count += 1

        # النشر اليومي
        categories = list(SOURCES.keys())
        random.shuffle(categories)
        for cat in categories:
            if published_count >= self.max_daily: break
            for url in SOURCES[cat]:
                feed = feedparser.parse(url)
                for e in feed.entries[:5]:
                    if published_count >= self.max_daily: break
                    keywords = self._extract_semantic_keywords(e.title, getattr(e, 'summary', ''))
                    if not self._is_duplicate_semantic(keywords):
                        ai_text = self._generate_ai(f"التصنيف: {cat}\nالموضوع: {e.title}\nالتفاصيل: {getattr(e, 'summary', '')}")
                        if ai_text and self.post_thread_with_retry(ai_text, e.link, e.title, cat, keywords):
                            published_count += 1
                            break

    def _generate_ai(self, context):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":STRICT_SYSTEM_PROMPT}, {"role":"user","content":context}],
                temperature=0.1
            )
            return r.choices[0].message.content.strip()
        except: return None

if __name__ == "__main__":
    TechEliteIntegrated2026().run_cycle()
