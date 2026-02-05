import os, sqlite3, logging, hashlib, re, time, random
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. الحوكمة السيادية - ضد الإغراق
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# مصادر نجبوية فقط لضمان الجودة
TRUSTED_SOURCES = ["techcrunch.com", "openai.com", "wired.com", "theverge.com", "bloomberg.com", "mit.edu"]

# 2. محرك الثريدات النخبوي (نظام النشر المتزن)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def post_thread(self, raw_content, source_url):
        system_prompt = (
            "أنت خبير تقني خليجي نخبوي. حوّل النص التالي إلى ثريد (Thread) متماسك جداً وبدون حشو.\n"
            "الهيكل: (Hook ذكي -> Analysis عميق ومختصر -> Takeaway استراتيجي).\n"
            "اللغة: خليجية بيضاء مهنية. افصل بين التغريدات بـ '---'."
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}],
                temperature=0.4 # تقليل التشتت لضمان الدقة
            )
            tweets = [t.strip() for t in r.choices[0].message.content.split("---") if len(t.strip()) > 30]

            prev_id = None
            for i, txt in enumerate(tweets):
                header = "🧵 رؤية تقنية\n" if i == 0 else f"↳ {i+1}/{len(tweets)}\n"
                footer = f"\n\n🔗 المرجع: {source_url}" if i == len(tweets)-1 else ""
                
                # --- Guard against Flooding (التأخير المتزن) ---
                if i > 0:
                    # تأخير عشوائي طويل بين 30 و 60 ثانية لكسر نمط الأتمتة
                    wait_time = random.randint(30, 60)
                    logging.info(f"⏳ تهدئة.. انتظار {wait_time} ثانية قبل الجزء القادم.")
                    time.sleep(wait_time)

                retry_count = 0
                while retry_count < 3:
                    try:
                        res = self.x.create_tweet(text=f"{header}{txt}{footer}", in_reply_to_tweet_id=prev_id)
                        prev_id = res.data['id']
                        break
                    except tweepy.TooManyRequests:
                        retry_count += 1
                        time.sleep(120 * retry_count) # انتظار مضاعف عند الضغط
            return True
        except Exception as e:
            logging.error(f"❌ خطأ في محرك النشر: {e}")
            return False

# 3. محرك الردود الذكي (محدد بـ 3 ردود فقط في الجلسة الواحدة لمنع الإغراق)
class SmartReplyEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def handle_mentions(self):
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me, max_results=5) 
            if not mentions.data: return

            count = 0
            with sqlite3.connect(DB_FILE) as conn:
                for tweet in mentions.data:
                    if count >= 3: break # حد أقصى للردود في كل تشغيل (Anti-Spam)
                    
                    rh = hashlib.sha256(f"rep_{tweet.id}".encode()).hexdigest()
                    if conn.execute("SELECT 1 FROM vault WHERE h=?", (rh,)).fetchone(): continue

                    prompt = f"رد كخبير تقني خليجي متمكن على: '{tweet.text}'. الرد يكون جملة واحدة قوية."
                    res = self.ai.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "user", "content": prompt}])
                    
                    time.sleep(random.randint(10, 20)) # تأخير قبل الرد
                    self.x.create_tweet(text=res.choices[0].message.content.strip(), in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (rh, "REPLY", datetime.now().isoformat()))
                    count += 1
                    logging.info(f"✅ رد ذكي متزن على: {tweet.id}")
        except Exception as e: logging.error(f"❌ خطأ الردود: {e}")

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
        # التحقق من المصدر ومنع التكرار
        domain = urlparse(url if "://" in url else f"https://{url}").netloc.replace("www.", "")
        if not any(t in domain for t in TRUSTED_SOURCES): return

        h = hashlib.sha256(content.encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone(): return
            
            if self.threader.post_thread(content, url):
                conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, "THREAD", datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEngine()
    bot.replier.handle_mentions()
    # تجربة محتوى نخبوي واحد فقط
    bot.publish_logic("مستقبل الحوسبة الحيوية ودمج الذكاء الاصطناعي في الخلايا البشرية لأغراض طبية.", "technologyreview.com")
