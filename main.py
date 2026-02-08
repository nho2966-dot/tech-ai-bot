import os, sqlite3, logging, hashlib, time, random
from datetime import datetime
import tweepy
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# سياسة الامتثال المحفوظة في الذاكرة
CONTENT_POLICY = (
    "أنت خبير تقني متمكن. تلتزم بالرد حصرياً على: "
    "1. الذكاء الاصطناعي 2. الأجهزة الذكية 3. الخوارزميات 4. الأمن السيبراني 5. الأخبار التقنية. "
    "القواعد: رد خليجي نخبوي، جملة واحدة مكثفة، لا هلوسة، لا خروج عن التخصص."
)

class SovereignEngineV43:
    def __init__(self):
        self._init_db()
        self._init_clients()

    def _init_db(self):
        with sqlite3.connect("tech_om_sovereign_v43.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def handle_responses(self):
        """المحرك المسؤول عن الردود الذكية (Mentions)"""
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me, tweet_fields=['author_id', 'text'])
            
            if not mentions.data:
                logging.info("📥 لا توجد إشارات (Mentions) جديدة.")
                return

            with sqlite3.connect("tech_om_sovereign_v43.db") as conn:
                for tweet in mentions.data:
                    h = hashlib.sha256(f"reply_{tweet.id}".encode()).hexdigest()
                    if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone(): continue

                    # فحص الامتثال قبل الرد
                    check_prompt = f"{CONTENT_POLICY}\nهل هذا السؤال تقني ممتثل؟ أجب بـ 'YES' أو 'NO'.\nالسؤال: {tweet.text}"
                    is_valid = self.ai.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", 
                                                              messages=[{"role": "user", "content": check_prompt}])
                    
                    if "YES" in is_valid.choices[0].message.content:
                        # توليد الرد النخبوي
                        reply_prompt = f"{CONTENT_POLICY}\nرد باحترافية على: {tweet.text}"
                        res = self.ai.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", 
                                                             messages=[{"role": "user", "content": reply_prompt}])
                        
                        reply_text = res.choices[0].message.content.strip()
                        
                        # تنفيذ الرد مع تأخير لمنع الحظر
                        time.sleep(random.randint(30, 60))
                        self.x.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                        logging.info(f"✅ تم الرد على التغريدة {tweet.id}")
                    
                    conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, "REPLY", datetime.now().isoformat()))
        except Exception as e:
            logging.error(f"❌ خطأ في محرك الردود: {e}")

if __name__ == "__main__":
    bot = SovereignEngineV43()
    # تشغيل محرك الردود أولاً
    bot.handle_responses()
