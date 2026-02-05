import os, sqlite3, logging, hashlib, re, time, random
from datetime import datetime
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. الحوكمة والتهدئة الإجبارية
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# 2. محرك النشر بنظام "التعافي الذكي" (Anti-429 Logic)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def post_thread(self, raw_content):
        timestamp = datetime.now().strftime("%H:%M")
        system_prompt = (
            f"أنت خبير تقني خليجي متمكن. حوّل النص التالي إلى ثريد احترافي.\n"
            f"تأكد أن التغريدة الأولى تنتهي بـ: (تحديث: {timestamp})"
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}]
            )
            tweets = [t.strip() for t in r.choices[0].message.content.split("---") if len(t.strip()) > 15]

            prev_id = None
            for i, txt in enumerate(tweets):
                retry_count = 0
                while retry_count < 3:
                    try:
                        # تأخير بشري رصين (بين 1.5 إلى 2.5 دقيقة بين كل تغريدة)
                        if i > 0:
                            wait_gap = random.randint(90, 150)
                            logging.info(f"⏳ تهدئة للمنصة.. انتظار {wait_gap} ثانية.")
                            time.sleep(wait_gap)

                        res = self.x.create_tweet(text=txt, in_reply_to_tweet_id=prev_id)
                        prev_id = res.data['id']
                        logging.info(f"✅ تم نشر الجزء {i+1}")
                        break # نجح النشر، انتقل للتغريدة التالية
                    
                    except tweepy.TooManyRequests:
                        retry_count += 1
                        # نظام السكون الإستراتيجي: انتظار 15 دقيقة عند أول صدام
                        sleep_time = 900 * retry_count 
                        logging.warning(f"🚨 قيود X (429)! سأدخل في سكون لمدة {sleep_time//60} دقيقة...")
                        time.sleep(sleep_time)
                    
                    except Exception as e:
                        logging.error(f"❌ خطأ غير متوقع: {e}")
                        return False
            return True
        except Exception as e:
            logging.error(f"❌ فشل محرك النشر: {e}")
            return False

# 3. الأوركسترا الرئيسية
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

    def run_strategy(self, topic):
        h = hashlib.sha256(f"{topic}_{datetime.now().strftime('%Y-%m-%d')}".encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone():
                logging.info("🔁 تم نشر محتوى هذا اليوم سابقاً.")
                return
            
            if self.threader.post_thread(topic):
                conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, "DAILY_THREAD", datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEngine()
    
    # محتوى نوعي يركز على الثورة الصناعية الرابعة للأفراد
    daily_topic = (
        "تحليل دور 'التصنيع الموزع' (Distributed Manufacturing) المعتمد على الذكاء الاصطناعي "
        "في تمكين الأفراد من إنشاء خطوط إنتاج منزلية منافسة للمصانع الكبرى في 2026."
    )
    
    bot.run_strategy(daily_topic)
