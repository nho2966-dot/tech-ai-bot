import os, sqlite3, logging, hashlib, time, random, textwrap
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والذاكرة الفائقة ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

NEWS_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss"
]

class TechSupremeArchitect:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 18
        self.last_ai_reset = datetime.now().date()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            # منع تكرار المحتوى المنشور
            conn.execute("CREATE TABLE IF NOT EXISTS content_memory (h TEXT PRIMARY KEY, dt TEXT)")
            # تحسين ذكي: منع تكرار الردود عبر الـ ID والـ Hash معاً
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
        if datetime.now().date() != self.last_ai_reset:
            self.ai_calls = 0
            self.last_ai_reset = datetime.now().date()
        
        if self.ai_calls >= self.MAX_AI_CALLS: return None

        # --- تحسين 1: برومبت منع الهلوسة الصارم (النسخة الذهبية) ---
        STRICT_SYSTEM = (
            sys_p + 
            "\nالتزم بالآتي بدقة:\n"
            "- اكتب بنقاط (Bullet Points) فقط.\n"
            "- لا تضف أي معلومة غير مؤكدة نهائياً.\n"
            "- اذكر اسم الأداة أو المصدر الرسمي صراحة.\n"
            "- أسلوب مختصر، تقني، بلا حشو أو آراء شخصية.\n"
            "- اللغة: عربية احترافية، المصطلحات الإنجليزية بين قوسين.\n"
        )

        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": STRICT_SYSTEM}, {"role": "user", "content": user_p}],
                temperature=0.15 # دقة متناهية
            )
            return r.choices[0].message.content
        except: return None

    # --- 2. المهام الاستراتيجية ---

    def task_scoop(self):
        # البحث عن سبق صحفي
        for url in NEWS_SOURCES:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            entry = feed.entries[0]
            h = hashlib.sha256(entry.title.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM content_memory WHERE h=?", (h,)).fetchone(): continue
            
            content = self._safe_ai_call("محلل سبق صحفي.", f"لخص هذا الخبر التقني بدقة للأفراد: {entry.title}")
            if content:
                self._publish_safe_thread(content, "🚨 سبق تقني عاجل:\n")
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO content_memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                return True
        return False

    def task_reply(self):
        # ردود احترافية مع منع تكرار معنوي
        query = "(\"كيف أستخدم AI\" OR #عمان_تتقدم) -is:retweet"
        tweets = self.x.search_recent_tweets(query=query, max_results=5, user_auth=True)
        if tweets.data:
            for t in tweets.data:
                text_hash = hashlib.sha256(t.text.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=? OR text_hash=?", (str(t.id), text_hash)).fetchone():
                        continue
                
                reply = self._safe_ai_call("مهندس ردود دقيقة.", f"حلل ورد باحترافية فائقة على: {t.text}")
                if reply:
                    self.x.create_tweet(text=f"{reply[:280]}", in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO tweet_history VALUES (?, ?, ?)", (str(t.id), text_hash, datetime.now().isoformat()))
                    return True
        return False

    def task_bomb_post(self):
        # نشر قنبلة تقنية (أدوات ذكاء اصطناعي أو ممارسات)
        content = self._safe_ai_call("خبير أدوات الذكاء الاصطناعي.", "اشرح أداة تقنية مذهلة توفر الوقت أو المال للأفراد.")
        if content:
            self._publish_safe_thread(content, "🚀 قنبلة تقنية:\n")
            return True
        return False

    def _publish_safe_thread(self, content, prefix=""):
        chunks = textwrap.wrap(content, width=250, break_long_words=False)
        prev_id = None
        for i, chunk in enumerate(chunks):
            # --- تحسين 2: إضافة حوافز النمو في آخر تغريدة ---
            if i == len(chunks) - 1:
                chunk += "\n\n🔁 إذا أفادك، أعد التغريد وتابع للحصريات التقنية."
            
            full_text = f"{prefix if i==0 else ''}{chunk} 🛡️ {i+1}/{len(chunks)}"
            tweet = self.x.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
            prev_id = tweet.data['id']
            time.sleep(45)

    def run_strategy(self):
        # موازنة النمو: 1. السبق 2. الردود 3. القنابل المعرفية
        if not self.task_scoop():
            if not self.task_reply():
                self.task_bomb_post()

if __name__ == "__main__":
    bot = TechSupremeArchitect()
    bot.run_strategy()
