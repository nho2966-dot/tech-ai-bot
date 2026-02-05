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

# 2. محرك الثريدات النخبوي (نظام النشر المتزن)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def post_thread(self, raw_content, source_url):
        system_prompt = (
            "أنت خبير تقني خليجي نخبوي. حوّل النص التالي إلى ثريد (Thread) متماسك.\n"
            "الهيكل: (Hook جذاب -> Analysis عميق -> Takeaway عملي).\n"
            "استخدم لهجة خليجية بيضاء، وافصل بين التغريدات بعلامة '---'."
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}]
            )
            tweets = [t.strip() for t in r.choices[0].message.content.split("---") if len(t.strip()) > 20]

            prev_id = None
            for i, txt in enumerate(tweets):
                if i > 0:
                    wait_time = random.randint(30, 60)
                    logging.info(f"⏳ انتظار {wait_time} ثانية لمنع الإغراق...")
                    time.sleep(wait_time)

                header = "🧵 رؤية تقنية\n" if i == 0 else f"↳ {i+1}/{len(tweets)}\n"
                footer = f"\n\n🔗 المرجع: {source_url}" if i == len(tweets)-1 else ""
                
                res = self.x.create_tweet(text=f"{header}{txt}{footer}", in_reply_to_tweet_id=prev_id)
                prev_id = res.data['id']
                logging.info(f"✅ تم نشر الجزء {i+1}")
            return True
        except Exception as e:
            logging.error(f"❌ خطأ في محرك النشر: {e}")
            return False

# 3. محرك الردود الذكي (المحصن ضد 403)
class SmartReplyEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def handle_mentions(self):
        try:
            me_res = self.x.get_me()
            if not me_res.data: return
            me_id = me_res.data.id

            mentions = self.x.get_users_mentions(id=me_id)
            if not mentions.data: 
                logging.info("📥 لا توجد منشنز جديدة.")
                return

            with sqlite3.connect(DB_FILE) as conn:
                for tweet in mentions.data:
                    rh = hashlib.sha256(f"rep_{tweet.id}".encode()).hexdigest()
                    if conn.execute("SELECT 1 FROM vault WHERE h=?", (rh,)).fetchone(): continue

                    logging.info(f"🧐 فحص التغريدة {tweet.id}")
                    
                    prompt = f"رد كخبير تقني خليجي متمكن بجملة واحدة على: '{tweet.text}'."
                    ai_res = self.ai.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    reply_text = ai_res.choices[0].message.content.strip()

                    try:
                        time.sleep(random.randint(5, 15))
                        self.x.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                        logging.info(f"✅ تم الرد بنجاح على {tweet.id}")
                    except tweepy.Forbidden:
                        logging.warning(f"⚠️ 403 على {tweet.id}: محاولة الرد البديل...")
                        try:
                            self.x.create_tweet(text="أهلاً بك، شكراً لتفاعلك التقني! 🛠️", in_reply_to_tweet_id=tweet.id)
                        except:
                            logging.error(f"❌ تعذر الرد النهائي على {tweet.id}")
                    
                    conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (rh, "REPLY_FINISH", datetime.now().isoformat()))
        except Exception as e:
            logging.error(f"❌ خطأ شامل في الردود: {e}")

# 4. الأوركسترا السيادية
class SovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.threader = EliteThreadEngine(self.x, self.ai)
        self.replier = SmartReplyEngine(self.x, self.ai)

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
        h = hashlib.sha256(content.encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone(): return
            if self.threader.post_thread(content, url):
                conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, "THREAD", datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEngine()
    # تشغيل محرك الردود أولاً
    bot.replier.handle_mentions()
    
    # محتوى استراتيجي يركز على الصناعة 4.0 والأفراد (الخيار 1)
    target_topic = "أدوات الذكاء الاصطناعي التي ستمكن الأفراد من بناء شركاتهم الخاصة في 2026 دون الحاجة لموظفين."
    bot.publish_logic(target_topic, "techcrunch.com")
