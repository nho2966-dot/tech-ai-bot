import os, sqlite3, logging, hashlib, re, time
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. الإعدادات والحوكمة
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

EDITORIAL_POLICY = {
    "BREAKING": {"min_score": 4, "max_len": 240, "prefix": "🚨 عاجل تقني"},
    "ANALYSIS": {"min_score": 5, "max_len": 25000, "prefix": "🧠 تحليل معمق"},
    "HARVEST":  {"min_score": 5, "max_len": 25000, "prefix": "🗞️ حصاد الأسبوع"}
}

TRUSTED_SOURCES = ["techcrunch.com", "openai.com", "wired.com", "theverge.com", "bloomberg.com"]

# 2. محرك الثريدات النخبوي (Thread & Completion Guard)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def _sanitize_and_guard(self, tweets):
        clean = []
        for t in tweets:
            t = t.strip()
            if len(t) < 45: continue
            if len(t) > 245: t = t[:242] + "..." # ضمان عدم الاقتطاع
            clean.append(t)
        return clean

    def post_thread(self, raw_content, source_url):
        prompt = "حوّل النص إلى ثريد خليجي (Hook -> Analysis -> Takeaway) مع فواصل '---'."
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": raw_content}], temperature=0.5
            )
            tweets = self._sanitize_and_guard(r.choices[0].message.content.split("---"))
            if len(tweets) < 3: return

            # Semantic Hook Guard
            if not re.search(r"(ليش|كيف|وش|هل|السبب)", tweets[0]):
                tweets[0] = "🔥 ليش هالموضوع يهمك الحين؟ خلّك معي.. 👇\n\n" + tweets[0]

            prev_id = None
            for i, txt in enumerate(tweets):
                header = "🧵 بداية التحليل\n" if i == 0 else f"↳ {i+1}/{len(tweets)}\n"
                footer = f"\n\n🔗 {source_url}" if i == len(tweets)-1 else ""
                
                # Takeaway Guard
                if i == len(tweets)-1 and "؟" not in txt:
                    txt += "\n\nوش رأيك؟ تتفق أو لا؟ 👇"

                time.sleep(1.5 if i == 0 else 0.8)
                res = self.x.create_tweet(text=f"{header}{txt}{footer}", in_reply_to_tweet_id=prev_id)
                prev_id = res.data['id']
            return prev_id
        except Exception as e: logging.error(f"❌ خطأ ثريد: {e}")

# 3. محرك الردود الذكي (Reply Engine)
class SmartReplyEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def handle_mentions(self):
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me, expansions=['author_id'])
            if not mentions.data: return

            with sqlite3.connect(DB_FILE) as conn:
                for tweet in mentions.data:
                    rh = hashlib.sha256(f"{tweet.id}".encode()).hexdigest()
                    if conn.execute("SELECT 1 FROM replies WHERE rh=?", (rh,)).fetchone(): continue

                    prompt = f"رد كخبير تقني خليجي باختصار وذكاء على: '{tweet.text}'. استعمل لهجة بيضاء وإيموجي."
                    res = self.ai.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "user", "content": prompt}])
                    
                    self.x.create_tweet(text=res.choices[0].message.content.strip(), in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO replies VALUES (?, ?, ?, ?)", (rh, tweet.id, tweet.author_id, datetime.now().isoformat()))
                    logging.info(f"✅ تم الرد على: {tweet.id}")
        except Exception as e: logging.error(f"❌ خطأ ردود: {e}")

# 4. المحرك الأساسي (Sovereign Engine)
class SovereignEngine:
    def __init__(self):
        self._init_clients()
        self._init_db()
        self.threader = EliteThreadEngine(self.x, self.ai)
        self.replier = SmartReplyEngine(self.x, self.ai)

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (rh TEXT PRIMARY KEY, tid TEXT, uid TEXT, dt TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN"), consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"), access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"))
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def publish_logic(self, raw_data, url, mode="ANALYSIS"):
        # (هنا يتم استدعاء AI للتحسين والسكور كما في الأكواد السابقة)
        # إذا السكور 5 والنمط تحليل، يتم تشغيل self.threader.post_thread
        pass

if __name__ == "__main__":
    bot = SovereignEngine()
    # 1. معالجة الردود أولاً
    bot.replier.handle_mentions()
    # 2. تشغيل اختبار حصاد الأسبوع (ثريد كامل)
    test_news = "Sora 2.0 يغير مفاهيم الإنتاج السينمائي، والذكاء الاصطناعي السيادي يصبح واقعاً في دول الخليج."
    bot.publish_logic(test_news, "techcrunch.com", mode="HARVEST")
