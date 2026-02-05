import os, sqlite3, logging, hashlib, time, random, textwrap
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- الإعدادات السيادية ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

TARGET_TOPICS = ["أدوات الذكاء الاصطناعي", "الإنتاجية الرقمية", "الأمن السيبراني", "الأتمتة الشخصية", "هندسة الأوامر", "تطبيقات الثورة الرابعة"]
NEWS_SOURCES = ["https://www.theverge.com/rss/index.xml", "https://www.wired.com/feed/rss"]
CTA_MAP = {"ai_tool": "📌 احفظ الأداة للفائدة.", "info": "🔁 أعد التغريد لنشر المعرفة.", "scoop": "🚀 تابعنا للحصول على السبق التقني.", "quiz": "💬 شاركنا برأيك في التعليقات."}
STYLE_MODES = ["3 نقاط مركزة جداً.", "نقطتان مع مثال تطبيقي.", "تحليل تقني مكثف مع نصيحة."]

class TechSovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 10 

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            # إنشاء الجدول إذا لم يكن موجوداً
            conn.execute("""CREATE TABLE IF NOT EXISTS content_memory 
                         (h TEXT PRIMARY KEY, h_link TEXT, type TEXT, topic TEXT, dt TEXT)""")
            
            # فحص وإضافة الأعمدة الناقصة في حال كانت قاعدة البيانات قديمة
            cursor = conn.execute("PRAGMA table_info(content_memory)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if "type" not in columns:
                conn.execute("ALTER TABLE content_memory ADD COLUMN type TEXT")
            if "topic" not in columns:
                conn.execute("ALTER TABLE content_memory ADD COLUMN topic TEXT")
            if "h_link" not in columns:
                conn.execute("ALTER TABLE content_memory ADD COLUMN h_link TEXT")
                
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, text_hash TEXT, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        style = random.choice(STYLE_MODES)
        STRICT_SYSTEM = (f"{sys_p}\n[المعايير: صفر هلوسة، دقة مهنية، لغة عربية سليمة]. النمط: {style}")
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": STRICT_SYSTEM}, {"role": "user", "content": user_p}],
                temperature=0.15
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def task_expert_reply(self):
        # محاولة الرد على محادثات تقنية لزيادة التفاعل
        query = "(الذكاء الاصطناعي OR تقنية) -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=5, user_auth=True)
            if not tweets or not tweets.data: return False
            for t in tweets.data:
                text_hash = hashlib.sha256(t.text.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM tweet_history WHERE text_hash=?", (text_hash,)).fetchone(): continue
                
                reply = self._safe_ai_call("خبير تقني في الثورة الرابعة.", f"رد بذكاء وعمق على هذه التغريدة: {t.text}")
                if reply:
                    self.x.create_tweet(text=reply[:280], in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO tweet_history VALUES (?, ?, ?)", (str(t.id), text_hash, datetime.now().isoformat()))
                    return True
        except Exception as e:
            logging.error(f"Reply Error: {e}")
            return False
        return False

    def task_scoop_and_content(self):
        task_type = random.choice(["ai_tool", "info", "scoop"])
        topic = random.choice(TARGET_TOPICS)
        
        prompt = f"اكتب تغريدة احترافية عن {topic} من نوع {task_type}. ركز على الفائدة العملية للفرد."
        content = self._safe_ai_call(f"محلل خبير في {topic}.", prompt)
        
        if content:
            h = hashlib.sha256(content.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO content_memory (h, type, topic, dt) VALUES (?, ?, ?, ?)", 
                             (h, task_type, topic, datetime.now().isoformat()))
            
            self.x.create_tweet(text=f"{content[:250]}\n\n{CTA_MAP.get(task_type, '')}")
            return True
        return False

    def run(self):
        # البوت يحاول الرد أولاً، إذا لم يجد هدفاً، يقوم بنشر محتوى جديد
        if not self.task_expert_reply():
            self.task_scoop_and_content()

if __name__ == "__main__":
    TechSovereignEngine().run()
