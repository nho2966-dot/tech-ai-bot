import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime, timedelta
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "news.db"
LOG_FILE = "error.log"

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s", 
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

class TechEliteSmartFilter:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            # إضافة عمود keywords لمنع التكرار الموضوعي
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    hash TEXT PRIMARY KEY, 
                    title TEXT, 
                    keywords TEXT, 
                    published_at TEXT
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

    def _extract_keywords(self, text):
        """استخراج الكلمات المفتاحية لمقارنة المحتوى موضوعياً"""
        # تنظيف النص واستخراج الكلمات الهامة (تبسيط للمثال)
        words = re.findall(r'\w+', text.lower())
        stop_words = {'the', 'a', 'in', 'on', 'at', 'for', 'with', 'microsoft', 'google'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return ",".join(list(set(keywords))[:5]) # حفظ أهم 5 كلمات

    def _is_duplicate_topic(self, new_keywords):
        """التحقق من وجود موضوع مشابه نُشر خلال الـ 24 ساعة الماضية"""
        with sqlite3.connect(DB_FILE) as conn:
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor = conn.execute("SELECT keywords FROM news WHERE published_at > ?", (yesterday,))
            existing_keywords = cursor.fetchall()
            
            new_set = set(new_keywords.split(','))
            for row in existing_keywords:
                existing_set = set(row[0].split(','))
                # إذا وجد تطابق في 3 كلمات مفتاحية أو أكثر، نعتبره مكرراً
                if len(new_set.intersection(existing_set)) >= 3:
                    return True
        return False

    def run_cycle(self):
        # ... (جلب الأخبار من المصادر المذكورة سابقاً)
        for url in SOURCES:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                current_keywords = self._extract_keywords(e.title)

                # فلترة مزدوجة: (بالرابط الـ Hash) + (بالموضوع Keywords)
                if not self._is_duplicate_topic(current_keywords):
                    ai_text = self._generate_ai(f"الموضوع: {e.title}")
                    if ai_text and self.post_thread(ai_text, e.link, e.title):
                        # حفظ الخبر مع بصمته الموضوعية
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT INTO news VALUES (?, ?, ?, ?)", 
                                         (h, e.title, current_keywords, datetime.now().isoformat()))
                        break # نشر خبر واحد والانتقال للدورة التالية لضمان التهدئة
