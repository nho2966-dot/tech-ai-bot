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

# 1. المصادر الموثوقة والهاشتاغات النخبوية
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
    "Education": ["#سلسلة_جوجل", "#تعلم_الذكاء_الاصطناعي"]
}

STRICT_SYSTEM_PROMPT = """
أنت رئيس تحرير تقني محترف ومحلل بيانات.
القواعد:
1. مثلث القيمة: [TWEET_1] خُطّاف جذاب، [TWEET_2] جوهر السر التقني، [POLL_QUESTION] سؤال استطلاع، [POLL_OPTIONS] خيارات مفصولة بـ (-).
2. العربية رصينة، مصطلحات إنجليزية بين قوسين.
3. ممنوع الهاشتاغات (#) داخل النص نهائياً.
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
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _clean_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def _generate_ai(self, prompt):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":STRICT_SYSTEM_PROMPT}, {"role":"user","content":prompt}],
                temperature=0.1
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"🤖 خطأ في الذكاء الاصطناعي: {e}")
            return None

    def analyze_yesterday_poll(self):
        """تحليل ونشر نتائج استطلاع اليوم السابق"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        with sqlite3.connect(DB_FILE) as conn:
            row = conn.execute("SELECT poll_id, title FROM news WHERE published_at LIKE ? AND poll_id IS NOT NULL", (f"{yesterday}%",)).fetchone()
            if not row: return
            
            try:
                tweet = self.x_client.get_tweet(id=row[0], expansions="attachments.poll_ids")
                if 'polls' in tweet.includes:
                    poll = tweet.includes['polls'][0]
                    results_text = "\n".join([f"- {opt['label']}: {opt['votes']} صوت" for opt in poll['options']])
                    analysis = self._generate_ai(f"حلل هذه النتائج لموضوع ({row[1]}):\n{results_text}\nأعطِ استنتاجاً واحداً.")
                    final_tweet = f"📊 نتائج استطلاع الأمس حول: {row[1]}\n\n{results_text}\n\n💡 التحليل:\n{analysis}\n#نتائج_TechElite"
                    self.x_client.create_tweet(text=final_tweet[:280])
            except Exception as e:
                logging.error(f"❌ خطأ تحليل استطلاع: {e}")

    def post_thread_with_retry(self, ai_text, url, title, cat, keywords):
        clean_url = self._clean_url(url)
        clean_ai_text = re.sub(r'#\w+', '', ai_text).strip()
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', clean_ai_text, re.S)
        if len(parts) < 3: return False
        
        tags = " ".join(random.sample(APPROVED_HASHTAGS.get(cat, ["#تقنية"]), 2))
        last_id = None
        poll_id = None
        
        for i, content in enumerate(parts[:3]):
            text = f"{i+1}/ {content.strip()}"
            if i == 1: text += f"\n\n🔗 المصدر:\n{clean_url}"
            if i == 2: text += f"\n\n{tags}"
            
            for attempt in range(3):
                try:
                    if i == 2 and len(parts) >= 4:
                        opts = [o.strip() for o in parts[3].split('-') if o.strip()][:4]
                        res = self.x_client.create_tweet(text=text[:280], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                        poll_id = res.data["id"]
                    else:
                        res = self.x_client.create_tweet(text=text[:280], in_reply_to_tweet_id=last_id)
                    last_id = res.data["id"]
                    time.sleep(75)
                    break
                except Exception as e:
                    logging.warning(f"⚠️ زحام أو خطأ، انتظار... {e}")
                    time.sleep(300)

        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO news VALUES (?, ?, ?, ?, ?, ?)", 
                         (hashlib.sha256(title.encode()).hexdigest(), title, cat, keywords, datetime.now().isoformat(), poll_id))
        return True

    def run_cycle(self):
        self.analyze_yesterday_poll()
        published_count = 0
        current_day = datetime.now().strftime('%A')
        
        # الأربعاء: سلسلة جوجل
        if current_day == "Wednesday":
            ai_text = self._generate_ai("ثريد تعليمي عن أحدث أداة Google AI وكيفية استخدامها باحترافية.")
            if ai_text and self.post_thread_with_retry(ai_text, "https://ai.google", "Google AI Deep Dive", "Education", "google,ai"):
                published_count += 1

        # النشر اليومي المتنوع
        categories = list(SOURCES.keys())
        random.shuffle(categories)
        for cat in categories:
            if published_count >= self.max_daily: break
            for url in SOURCES[cat]:
                feed = feedparser.parse(url)
                for e in feed.entries[:3]:
                    if published_count >= self.max_daily: break
                    h = hashlib.sha256(e.title.encode()).hexdigest()
                    with sqlite3.connect(DB_FILE) as conn:
                        if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                            ai_text = self._generate_ai(f"الموضوع: {e.title}\nالتفاصيل: {getattr(e, 'summary', '')}")
                            if ai_text and self.post_thread_with_retry(ai_text, e.link, e.title, cat, "news"):
                                published_count += 1
                                break

if __name__ == "__main__":
    TechEliteUltimate2026().run_cycle()
