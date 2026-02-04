import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from tweepy.errors import TweepyException, TooManyRequests

load_dotenv()
DB_FILE = "news.db"
LOG_FILE = "error.log"
MAX_DAILY = 3 
MAX_LEN = 280

# إعداد السجلات (Logs)
logging.basicConfig(
    level=logging.INFO,
    format="🛡️ %(asctime)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

# 1. المرجع المعرفي والقوائم (الالتزام بالبنود السابقة)
KNOWLEDGE_BASE = {
    "microsoft": "خبايا Microsoft 365، اختصارات الإنتاجية، ميزات Windows 11.",
    "x_profit": "أرباح الردود (0.2 سنت)، مشاهدات الموثقين، استراتيجية آخر 20 منشور.",
    "google_ai": "سلسلة أسبوعية دورية تشرح أدوات جوجل للذكاء الاصطناعي باحترافية."
}

GOOGLE_AI_TOOLS = [
    {"name": "Google Gemini", "focus": "تحليل البيانات الضخمة والبحث المتقدم."},
    {"name": "Google Vertex AI", "focus": "تطوير نماذج الذكاء الاصطناعي للمؤسسات."},
    {"name": "Google NotebookLM", "focus": "إدارة المعرفة والوثائق الشخصية."},
    {"name": "Google Imagen 3", "focus": "توليد الصور الاحترافية فائقة الدقة."},
    {"name": "Google Workspace AI", "focus": "رفع الإنتاجية في تطبيقات العمل الذكية."}
]

SOURCES = [
    "https://venturebeat.com/category/ai/feed/", 
    "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    "https://windowscentral.com/rss.xml", 
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml"
]

# 2. البرومبت الشامل (يجمع الأسلوب المبتكر + الهاشتاغات + تنوع المحتوى)
STRICT_SYSTEM_PROMPT = f"""
أنت رئيس تحرير (TechElite). صُغ محتوى تقنياً احترافياً جداً.
المراجع المعتمدة: {KNOWLEDGE_BASE}
القواعد القطعية:
1. نوع أسلوب العرض بين (ثريد إخباري، قائمة Top 5، نصيحة تقنية).
2. استخدم 'مثلث القيمة': [TWEET_1] خُطّاف جذاب، [TWEET_2] جوهر السر، [POLL_QUESTION] تفاعل.
3. العربية ودودة ورصينة، مع مصطلحات إنجليزية بين قوسين (Term).
4. توليد 3 هاشتاغات ديناميكية ذكية في نهاية الثريد.
5. منع الرموز الصينية أو HTML تماماً.
"""

class TechEliteFinalMaster:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_clean(self, text):
        return not re.search(r'[\u4e00-\u9fff]|<.*?>', text)

    def post_thread(self, ai_text, url):
        parts = re.findall(r'\[.*?\](.*?)(?=\[|$)', ai_text, re.S)
        if len(parts) < 3: return False

        last_id = None
        for i, content in enumerate(parts[:3]):
            text = f"{i+1}/ {content.strip()}"
            if i == 1: text += f"\n\n🔗 {url}"
            
            try:
                if i == 2 and len(parts) >= 4:
                    opts = [o.strip() for o in parts[3].split('-') if o.strip()][:4]
                    res = self.x_client.create_tweet(text=text[:MAX_LEN], poll_options=opts, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                else:
                    res = self.x_client.create_tweet(text=text[:MAX_LEN], in_reply_to_tweet_id=last_id)
                
                last_id = res.data["id"]
                time.sleep(70) 
            except TooManyRequests as e:
                wait = int(e.response.headers.get('Retry-After', 300))
                logging.warning(f"⚠️ زحام API، انتظار {wait} ثانية")
                time.sleep(wait)
            except Exception as e:
                logging.error(f"❌ خطأ نشر: {e}")
        return True

    def run_cycle(self):
        current_day = datetime.now().strftime('%A')
        published_count = 0
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # الأربعاء: تفعيل بروتوكول سلسلة جوجل AI
        if current_day == "Wednesday":
            week_idx = datetime.now().isocalendar()[1] % len(GOOGLE_AI_TOOLS)
            tool = GOOGLE_AI_TOOLS[week_idx]
            ai_text = self._generate_ai(f"سلسلة الأسبوع: أداة {tool['name']}. التركيز: {tool['focus']}. اشرح المميزات وكيفية الاستغلال الاحترافي.")
            if ai_text and self.post_thread(ai_text, "https://ai.google/"):
                published_count = 1

        # النشر اليومي (أخبار + قوائم + نصائح)
        random.shuffle(SOURCES)
        for url in SOURCES:
            if published_count >= MAX_DAILY: break
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                if published_count >= MAX_DAILY: break
                h = hashlib.sha256(e.title.encode()).hexdigest()
                cursor.execute("SELECT 1 FROM news WHERE hash=?", (h,))
                if not cursor.fetchone():
                    ai_text = self._generate_ai(f"الموضوع: {e.title}\nالتفاصيل: {getattr(e, 'summary', '')}")
                    if ai_text and self.post_thread(ai_text, e.link):
                        cursor.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        published_count += 1
        conn.close()

    def _generate_ai(self, context):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":STRICT_SYSTEM_PROMPT},{"role":"user","content":context}],
                temperature=0.1
            )
            content = r.choices[0].message.content.strip()
            return content if self._is_clean(content) else None
        except Exception as e:
            logging.error(f"🤖 خطأ AI: {e}"); return None

if __name__ == "__main__":
    TechEliteFinalMaster().run_cycle()
