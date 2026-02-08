import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignAgentV76:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss"
        ]
        self.charter = "أنت مستشار تقني خليجي نخبوي. ردودك رصينة، دقيقة، وتستخدم مصطلحات تقنية بين قوسين ()."

    def _init_db(self):
        with sqlite3.connect("sovereign_v76.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        # تفعيل التحميل المتأني لتجنب Throttling
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False # سنقوم نحن بإدارة الانتظار يدوياً
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def handle_mentions(self):
        """التعامل مع الإشارات بذكاء انتقائي"""
        with sqlite3.connect("sovereign_v76.db") as conn:
            res = conn.execute("SELECT last_run FROM throttle WHERE task='mentions'").fetchone()
            if res and datetime.now() < datetime.fromisoformat(res[0]) + timedelta(minutes=30):
                logging.info("⏳ Mentions guard active. Skipping this round.")
                return

        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, max_results=5) # تقليل العدد لـ 5 فقط
            if not mentions.data: return

            for t in mentions.data:
                h = hashlib.sha256(f"reply_{t.id}".encode()).hexdigest()
                with sqlite3.connect("sovereign_v76.db") as conn:
                    if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    
                    # إنتاج الرد النخبوي
                    reply_txt = self.ai.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=[{"role": "system", "content": self.charter}, 
                                  {"role": "user", "content": f"رد بلهجة خليجية نُخبوية: {t.text}"}],
                        temperature=0.1
                    ).choices[0].message.content.strip()

                    if reply_txt:
                        self.x.create_tweet(text=reply_txt, in_reply_to_tweet_id=t.id)
                        conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        conn.commit()
                        logging.info(f"✅ Replied to: {t.id}")
                        time.sleep(120) # انتظار دقيقتين بين كل رد وآخر

            with sqlite3.connect("sovereign_v76.db") as conn:
                conn.execute("INSERT OR REPLACE INTO throttle VALUES ('mentions', ?)", (datetime.now().isoformat(),))
                conn.commit()

        except tweepy.errors.TooManyRequests:
            logging.warning("⚠️ X Rate Limit hit. Saving state and exiting.")
        except Exception as e:
            logging.error(f"Error: {e}")

if __name__ == "__main__":
    bot = SovereignAgentV76()
    bot.handle_mentions()
    # يتم استدعاء الوظائف الأخرى بنفس النمط الهادئ
