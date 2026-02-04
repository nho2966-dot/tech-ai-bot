import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlparse

# إعداد البيئة
load_dotenv()
DB_FILE = "news_master_2026.db"
LOG_FILE = "system_master.log"

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

# 1. المصادر الرسمية (تم التأكد من سلامة روابطها)
SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default", "https://krebsonsecurity.com/feed/"],
    "FinTech_Crypto": ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://www.theblock.co/rss.xml"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"],
    "Tech_Authority": ["https://arstechnica.com/feed/", "https://www.wired.com/feed/rss"]
}

# 2. القائمة البيضاء للهاشتاغات (منعاً للحسابات غير الموثوقة)
APPROVED_HASHTAGS = {
    "AI_Official": ["#الذكاء_الاصطناعي", "#AI", "#GoogleGemini", "#TechNews"],
    "CyberSecurity": ["#الأمن_السيبراني", "#CyberSecurity", "#امن_المعلومات"],
    "FinTech_Crypto": ["#التقنية_المالية", "#FinTech", "#بلوكشين"],
    "Microsoft_Official": ["#مايكروسوفت", "#أسرار_التقنية", "#Windows11"],
    "Education": ["#سلسلة_جوجل", "#نصائح_تقنية", "#تعلم_الذكاء_الاصطناعي"]
}

STRICT_SYSTEM_PROMPT = """
أنت رئيس تحرير تقني محترف. صُغ المحتوى بناءً على المصادر الرسمية.
القواعد:
1. مثلث القيمة: [TWEET_1] خُطّاف، [TWEET_2] جوهر السر، [POLL_QUESTION] تفاعل.
2. العربية رصينة، مصطلحات إنجليزية بين قوسين.
3. ممنوع نهائياً كتابة أي هاشتاغات (#) داخل النص؛ سيقوم النظام بإضافتها برمجياً.
"""

class TechEliteFinal2026:
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

    def _clean_url(self, url):
        """تنظيف الرابط لضمان عمله على متصفحات الجوال وتويتر"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def post_thread(self, ai_text, url, title, cat, keywords):
        # 1. تنظيف الرابط
        clean_url = self._clean_url(url)
        # 2. إزالة أي هاشتاغات عشوائية قد يولدها الـ AI
        clean_ai_text = re.sub(r'#\w+', '', ai_text).strip()
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', clean_ai_text, re.S)
        if len(parts) < 3: return False
        
        # 3. اختيار هاشتاغات موثوقة
        tags = " ".join(random.sample(APPROVED_HASHTAGS.get(cat, ["#تقنية"]), 2))
        last_id = None
        
        for i, content in enumerate(parts[:3]):
            text = f"{i+1}/ {content.strip()}"
            if i == 1: text += f"\n\n🔗 المصدر الرسمي:\n{clean_url}" # الرابط في سطر مستقل لضمان التفعيل
            if i == 2: text += f"\n\n{tags}"
            
            try:
                if i == 2 and len(parts) >= 4:
                    opts = [o.strip() for o in parts[3].split('-') if o.strip()][:4]
                    res = self.x_client.create_tweet(text=text[:280], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                else:
                    res = self.x_client.create_tweet(text=text[:280], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(80) # زيادة وقت الأمان
            except Exception as e:
                logging.error(f"❌ خطأ نشر: {e}")
                break
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO news VALUES (?, ?, ?, ?, ?, ?)", 
                         (hashlib.sha256(title.encode()).hexdigest(), title, cat, keywords, tags, datetime.now().isoformat()))
        return True

    def run_cycle(self):
        # (نفس منطق الجلب السابق مع استخدام _clean_url)
        pass

if __name__ == "__main__":
    bot = TechEliteFinal2026()
    # لتجربة التشغيل اليدوي والتأكد من الروابط
    bot.run_cycle()
