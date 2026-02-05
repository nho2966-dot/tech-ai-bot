import os, sqlite3, logging, hashlib, re, time, random
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. الإعدادات
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

TRUSTED_SOURCES = ["techcrunch.com", "openai.com", "wired.com", "theverge.com", "bloomberg.com", "mit.edu"]

# 2. محرك النشر (المجرب والناجح)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def post_thread(self, raw_content, source_url):
        system_prompt = "أنت خبير تقني خليجي. حوّل النص لثريد مهني بلهجة بيضاء، افصل بـ '---'."
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_content}]
            )
            tweets = [t.strip() for t in r.choices[0].message.content.split("---") if len(t.strip()) > 20]
            
            prev_id = None
            for i, txt in enumerate(tweets):
                # تأخير متزن لمنع الإغراق
                if i > 0: time.sleep(random.randint(20, 40))
                
                res = self.x.create_tweet(text=f"{txt}\n\n{i+1}/{len(tweets)}", in_reply_to_tweet_id=prev_id)
                prev_id = res.data['id']
                logging.info(f"✅ تم نشر جزء {i+1}")
            return True
        except Exception as e:
            logging.error(f"❌ خطأ في النشر: {e}")
            return False

# 3. محرك الردود (مع معالجة خطأ 403)
class SmartReplyEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def handle_mentions(self):
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me)
            # ... باقي منطق الردود
        except tweepy.Forbidden:
            logging.warning("⚠️ الوصول للمنشنز مرفوض حالياً (403). سأكتفي بالنشر فقط.")
        except Exception as e:
            logging.error(f"❌ خطأ ردود: {e}")

# 4. المحرك الرئيسي
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
    # تشغيل الردود بشكل مستقل (لو فشلت ما تخرب النشر)
    bot.replier.handle_mentions()
    
    # النشر الإستراتيجي (المحتوى الذي نجح سابقاً)
    bot.publish_logic("تطور تقنيات الجيل السادس 6G وبداية التجارب الحقيقية في المدن الذكية.", "wired.com")
