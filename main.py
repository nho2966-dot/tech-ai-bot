import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlparse

# إعداد البيئة
load_dotenv()
DB_FILE = "tech_elite_final.db"
LOG_FILE = "system.log"

logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

# 1. المصادر الموثقة والهاشتاغات النخبوية
SOURCES = {
    "AI_Official": ["https://blog.google/technology/ai/rss/", "https://openai.com/news/rss/"],
    "CyberSecurity": ["https://thehackernews.com/feeds/posts/default", "https://krebsonsecurity.com/feed/"],
    "FinTech_Crypto": ["https://www.coindesk.com/arc/outboundfeeds/rss/"],
    "Microsoft_Official": ["https://www.microsoft.com/en-us/microsoft-365/blog/feed/"]
}

APPROVED_HASHTAGS = {
    "AI_Official": ["#الذكاء_الاصطناعي", "#AI", "#TechNews"],
    "CyberSecurity": ["#الأمن_السيبراني", "#CyberSecurity"],
    "FinTech_Crypto": ["#التقنية_المالية", "#FinTech"],
    "Microsoft_Official": ["#مايكروسوفت", "#أسرار_التقنية"],
    "Education": ["#سلسلة_جوجل", "#نصائح_تقنية"]
}

STRICT_SYSTEM_PROMPT = """
أنت محلل تقني محترف. صُغ المحتوى بناءً على المصادر الرسمية.
القواعد:
1. مثلث القيمة: [TWEET_1] خُطّاف، [TWEET_2] جوهر السر، [POLL_QUESTION] سؤال استطلاع، [POLL_OPTIONS] خيارات (مفصولة بـ -).
2. العربية رصينة، مصطلحات إنجليزية بين قوسين.
3. التزم بتحليل نتائج الاستطلاع بأسلوب منطقي وعلمي.
"""

class TechEliteMaster2026:
    def __init__(self):
        self._init_db()
        self._init_clients()

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

    def post_thread(self, ai_text, url, title, cat, keywords):
        clean_url = self._clean_url(url)
        clean_ai_text = re.sub(r'#\w+', '', ai_text).strip()
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', clean_ai_text, re.S)
        if len(parts) < 3: return False
        
        tags = " ".join(random.sample(APPROVED_HASHTAGS.get(cat, ["#تقنية"]), 2))
        last_id = None
        poll_id = None
        
        for i, content in enumerate(parts[:3]):
            text = f"{i+1}/ {content.strip()}"
            if i == 1: text += f"\n\n🔗 المصدر الرسمي:\n{clean_url}"
            if i == 2: text += f"\n\n{tags}"
            
            try:
                # إضافة الاستطلاع في التغريدة الأخيرة
                if i == 2 and len(parts) >= 4:
                    opts = [o.strip() for o in parts[3].split('-') if o.strip()][:4]
                    res = self.x_client.create_tweet(text=text[:280], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                    poll_id = res.data["id"]
                else:
                    res = self.x_client.create_tweet(text=text[:280], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(80)
            except Exception as e:
                logging.error(f"❌ خطأ نشر: {e}"); break
        
        # حفظ الـ poll_id لتحليله غداً
        if poll_id:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT OR REPLACE INTO news VALUES (?, ?, ?, ?, ?, ?)", 
                             (hashlib.sha256(title.encode()).hexdigest(), title, cat, keywords, datetime.now().isoformat(), poll_id))
        return True

    def analyze_yesterday_poll(self):
        """سحب نتائج استطلاع الأمس ونشر تحليلها"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        with sqlite3.connect(DB_FILE) as conn:
            row = conn.execute("SELECT poll_id, title FROM news WHERE published_at LIKE ?", (f"{yesterday}%",)).fetchone()
            if not row or not row[0]: return
            
            try:
                tweet = self.x_client.get_tweet(id=row[0], expansions="attachments.poll_ids")
                poll = tweet.includes['polls'][0]
                results = "\n".join([f"- {opt['label']}: {opt['votes']} صوت" for opt in poll['options']])
                
                # توليد تحليل ذكي
                analysis_prompt = f"حلل منطقياً نتائج هذا الاستطلاع التقني حول موضوع ({row[1]}):\n{results}\nأعطِ استنتاجاً واحداً ذكياً للمجتمع التقني."
                analysis = self._generate_ai(analysis_prompt)
                
                final_text = f"📊 نتائج استطلاع الأمس حول: {row[1]}\n\n{results}\n\n💡 التحليل المنطقي:\n{analysis}\n#نتائج_TechElite"
                self.x_client.create_tweet(text=final_text[:280])
                logging.info("✅ تم نشر تحليل الاستطلاع.")
            except Exception as e:
                logging.error(f"❌ فشل تحليل الاستطلاع: {e}")

    def _generate_ai(self, context):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":STRICT_SYSTEM_PROMPT}, {"role":"user","content":context}],
                temperature=0.1
            )
            return r.choices[0].message.content.strip()
        except: return None

    def run_cycle(self):
        # 1. تحليل استطلاع الأمس أولاً
        self.analyze_yesterday_poll()
        # 2. دورة النشر اليومية (جوجل AI الأربعاء، إلخ...)
        # ... (نفس منطق النشر السابق)
