import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

POLICY = (
    "أنت محرر تقني خليجي نخبوي. القواعد:\n"
    "1. اللغة: العربية (الخليجية) مع مصطلحات إنجليزية بين قوسين ().\n"
    "2. الهيكل: (Hook) -> (Value) -> (Impact) -> (CTA).\n"
    "3. التخصص: AI، أجهزة، خوارزميات، أمن، سكوبات.\n"
    "4. الموانع: لا رد على النفس، لا تكرار، لا رموز غير مفهومة، لا لغات هجينة."
)

class SovereignEliteSystem:
    def __init__(self):
        self._setup_db()
        self._setup_clients()
        self.bot_id = self.x.get_me().data.id

    def _setup_db(self):
        with sqlite3.connect("sovereign_v49.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS v (h PRIMARY KEY, type TEXT, dt TEXT)")

    def _setup_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def is_clean(self, text):
        """فلتر لمنع اللغات والرموز غير المفهومة"""
        # السماح فقط بالأحرف العربية، الإنجليزية، الأرقام، والرموز الأساسية ((), . ! ?)
        clean_pattern = re.compile(r'^[ \u0600-\u06FF\u0750-\u077F0-9a-zA-Z()\[\]\.\!\?\-\n\r]+$')
        if not clean_pattern.match(text):
            return False
        # منع تكرار الرموز بشكل مريب (مثل ؟؟؟؟؟ أو !!!!!)
        if re.search(r'[\?\!\.]{4,}', text):
            return False
        return True

    def _ai_call(self, user_p):
        for _ in range(3): # محاولة إعادة التوليد إذا كان النص غير نظيف
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": POLICY}, {"role": "user", "content": user_p}]
            ).choices[0].message.content.strip()
            
            if self.is_clean(res):
                return res
        return "" # إيقاف النشر إذا فشلت المحاولات لضمان الجودة

    def handle_mentions(self):
        mentions = self.x.get_users_mentions(id=self.bot_id, tweet_fields=['author_id', 'text'])
        if not mentions.data: return
        with sqlite3.connect("sovereign_v49.db") as conn:
            for t in mentions.data:
                h = hashlib.sha256(f"{t.author_id}_{t.id}".encode()).hexdigest()
                if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM v WHERE h=?", (h,)).fetchone():
                    continue
                
                reply = self._ai_call(f"رد بالخليجية مع مصطلحات بين قوسين: {t.text}")
                if reply:
                    time.sleep(random.randint(45, 90))
                    self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                    conn.execute("INSERT INTO v VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))

    def post_scoop_thread(self):
        feed = feedparser.parse("https://techcrunch.com/feed/")
        if not feed.entries: return
        entry = feed.entries[0]
        h = hashlib.sha256(entry.title.encode()).hexdigest()
        
        with sqlite3.connect("sovereign_v49.db") as conn:
            if conn.execute("SELECT 1 FROM v WHERE h=?", (h,)).fetchone(): return
            
            instr = f"حول الخبر لثريد خليجي (Hook-Value-Impact-CTA) بمصطلحات بين قوسين، فواصل '---':\n{entry.title}"
            raw_content = self._ai_call(instr)
            if not raw_content: return
            
            tweets = [t.strip() for t in raw_content.split("---") if len(t.strip()) > 5]
            p_id = None
            for i, txt in enumerate(tweets):
                time.sleep(random.randint(120, 200))
                msg = f"{txt}\n.\n🕒 {datetime.now().strftime('%H:%M')}" if i == 0 else txt
                res = self.x.create_tweet(text=msg, in_reply_to_tweet_id=p_id)
                p_id = res.data['id']
            conn.execute("INSERT INTO v VALUES (?,?,?)", (h, "THREAD", datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEliteSystem()
    bot.post_scoop_thread()
    bot.handle_mentions()
