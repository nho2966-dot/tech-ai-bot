import os, sqlite3, logging, hashlib, time, random
from datetime import datetime
import tweepy
import feedparser
from openai import OpenAI
from dotenv import load_dotenv

# إعداد البيئة
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

# السياسة الصارمة (AI, Smart Devices, Algorithms, Cybersecurity, Scoops)
POLICY = (
    "خبير تقني خليجي نخبوي. الهيكل: (Hook) ثم (Value) ثم (Impact) ثم (CTA). "
    "التخصص: الذكاء الاصطناعي، الأجهزة الذكية، الخوارزميات، الأمن السيبراني، الأخبار الحصرية. "
    "يُمنع: الثورة الصناعية 4، الهلوسة، القص، الرد على النفس، الرد المكرر."
)

class SovereignSystem:
    def __init__(self):
        self._setup_db()
        self._setup_clients()
        self.bot_id = self.x.get_me().data.id

    def _setup_db(self):
        with sqlite3.connect("sovereign_v46.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS v (h PRIMARY KEY, type TEXT, dt TEXT)")

    def _setup_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _ai_call(self, system_p, user_p):
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_p}, {"role": "user", "content": user_p}]
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return ""

    def handle_mentions(self):
        """محرك الردود بفلتر صارم لمنع الرد على النفس والتكرار"""
        mentions = self.x.get_users_mentions(id=self.bot_id, tweet_fields=['author_id'])
        if not mentions.data: return
        
        with sqlite3.connect("sovereign_v46.db") as conn:
            for t in mentions.data:
                # الفلتر الصارم المزدوج
                h = hashlib.sha256(f"{t.author_id}_{t.id}".encode()).hexdigest()
                if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM v WHERE h=?", (h,)).fetchone():
                    continue

                if "YES" in self._ai_call(POLICY, f"هل السؤال تقني ممتثل؟ YES/NO: {t.text}"):
                    reply = self._ai_call(POLICY, f"رد باحترافية جملة واحدة: {t.text}")
                    time.sleep(random.randint(40, 80))
                    self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                    conn.execute("INSERT INTO v VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))

    def post_scoop_thread(self):
        """جلب أخبار حصرية ونشرها كثريد احترافي"""
        feed = feedparser.parse("https://techcrunch.com/feed/")
        if not feed.entries: return
        
        entry = feed.entries[0]
        h = hashlib.sha256(entry.title.encode()).hexdigest()
        
        with sqlite3.connect("sovereign_v46.db") as conn:
            if conn.execute("SELECT 1 FROM v WHERE h=?", (h,)).fetchone(): return
            
            content = self._ai_call(POLICY, f"صغ ثريد (Hook-Value-Impact-CTA) مقسم بـ '---' حول: {entry.title}\n{entry.description}")
            tweets = [t.strip() for t in content.split("---") if len(t.strip()) > 5]
            
            p_id = None
            for i, txt in enumerate(tweets):
                time.sleep(random.randint(120, 180))
                # إضافة بصمة زمنية لمنع خطأ 403 Duplicate
                msg = f"{txt}\n.\n🕒 {datetime.now().strftime('%H:%M')}" if i == 0 else txt
                res = self.x.create_tweet(text=msg, in_reply_to_tweet_id=p_id)
                p_id = res.data['id']
            
            conn.execute("INSERT INTO v VALUES (?,?,?)", (h, "THREAD", datetime.now().isoformat()))

    def run_daily_cycle(self):
        """تشغيل الدورة الكاملة (نشر + ردود)"""
        logging.info("🚀 بدء الدورة التقنية...")
        self.post_scoop_thread() # نشر المحتوى الجديد
        self.handle_mentions()   # الرد على المتابعين بذكاء
        logging.info("✅ اكتملت الدورة بنجاح.")

if __name__ == "__main__":
    bot = SovereignSystem()
    bot.run_daily_cycle()
