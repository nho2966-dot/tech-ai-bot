import os, sqlite3, logging, hashlib, re, time, random
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. الحوكمة والإعدادات
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

TRUSTED_SOURCES = ["techcrunch.com", "openai.com", "wired.com", "theverge.com", "bloomberg.com", "mit.edu"]

# 2. محرك النشر النخبوي (مع بصمة زمنية فريدة)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def post_thread(self, raw_content, source_url):
        # إضافة بصمة زمنية للنص لمنع خطأ 403 (Duplicate)
        timestamp = datetime.now().strftime("%H:%M:%S")
        system_prompt = (
            f"أنت خبير تقني خليجي. حوّل النص التالي لثريد مهني.\n"
            f"ملاحظة: اجعل الخاتمة تحتوي على وقت التحديث: {timestamp}"
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}]
            )
            tweets = [t.strip() for t in r.choices[0].message.content.split("---") if len(t.strip()) > 10]

            prev_id = None
            for i, txt in enumerate(tweets):
                if i > 0: time.sleep(random.randint(30, 45))
                
                # إضافة معرف فريد غير مرئي تقريباً بنهاية أول تغريدة
                final_txt = f"{txt}\n.\n{timestamp}" if i == 0 else txt
                
                res = self.x.create_tweet(text=final_txt, in_reply_to_tweet_id=prev_id)
                prev_id = res.data['id']
                logging.info(f"✅ تم نشر التغريدة {i+1} بنجاح.")
            return True
        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")
            return False

# 3. المحرك الرئيسي
class SovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.threader = EliteThreadEngine(self.x, self.ai)

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def publish_logic(self, content, url):
        # بصمة المحتوى للتأكد من عدم التكرار البرمجي
        h = hashlib.sha256(f"{content}_{datetime.now().day}".encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone():
                logging.info("🔁 تم نشر هذا المحتوى اليوم بالفعل.")
                return
            
            if self.threader.post_thread(content, url):
                conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, "THREAD", datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEngine()
    
    # موضوع جديد كلياً لمنع الـ 403 الناتج عن التكرار
    new_topic = "تحليل استراتيجي لأثر الحوسبة الكمية (Quantum Computing) على أمن البيانات الشخصية للأفراد في عام 2026."
    bot.publish_logic(new_topic, "mit.edu")
