import os, sqlite3, logging, hashlib, time, random, textwrap
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والذاكرة ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. المجالات الستة (بصيغة ودية للأفراد) ---
TARGET_TOPICS = [
    "كيف تبدع باستخدام الذكاء الاصطناعي في يومك (ChatGPT, MidJourney) وتسهل مهامك",
    "أسرار وحيل في هاتفك الذكي (iPhone, Samsung) تخلي استخدامك أسرع وأذكى",
    "عالم الألعاب والواقع المعزز (VR/AR) وكيف تستمتع بأحدث تقنيات الترفيه",
    "تطبيقات رهيبة تساعدك تنظم وقتك، تهتم بصحتك، أو حتى تبدع في المونتاج",
    "خطوات بسيطة وسلسة تحمي فيها خصوصيتك وتأمن حساباتك من أي اختراق",
    "تحديات تقنية وألغاز ذكاء اصطناعي (AI Quiz) تحرك فيها عقلك وتستمتع"
]

SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://www.technologyreview.com/feed/"
]

class TechSupremeFriendly:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 25
        try:
            me = self.x.get_me()
            self.my_user_id = str(me.data.id)
            logging.info(f"✅ أهلاً بك! البوت متصل الآن كصديق تقني.")
        except: self.my_user_id = None

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _safe_ai_call(self, sys_p, user_p):
        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": sys_p + " الأسلوب: ودي، سلس، بسيط، بعيد عن التكلف، استخدم نقاط واضحة ومصطلحات إنجليزية بين قوسين."},
                    {"role": "user", "content": user_p}
                ],
                temperature=0.4 # زيادة طفيفة للإبداع في اللغة الودية
            )
            return r.choices[0].message.content
        except: return None

    # --- 3. نظام النشر السلس (منع الاقتطاع) ---
    def _publish_safe_thread(self, content, prefix=""):
        # تقسيم النص لضمان سلاسة القراءة (260 حرف لتجنب الاقتطاع)
        chunks = textwrap.wrap(content, width=260, break_long_words=False)
        prev_id = None
        for i, chunk in enumerate(chunks):
            try:
                # إضافة إيموجي ورمز السلسلة بشكل لطيف
                marker = f" ✨ ({i+1}/{len(chunks)})"
                full_text = f"{prefix if i==0 else ''}{chunk}{marker}"
                tweet = self.x.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
                prev_id = tweet.data['id']
                time.sleep(40) 
            except: break

    # --- 4. المهام بروح "الصديق التقني" ---
    def task_scoop(self):
        logging.info("🕵️ بشوف إذا فيه أخبار تقنية جديدة تهمنا...")
        for url in SOURCES:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            latest = feed.entries[0]
            h = hashlib.sha256(latest.title.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue

            content = self._safe_ai_call("🚨 خبر عاجل بأسلوب مشوق:", f"بسط هذا الخبر [{latest.title}] ووضح كيف بيفيدنا كأفراد.")
            if content:
                self._publish_safe_thread(content, "🚨 خبر يهمك على السريع:\n")
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("INSERT INTO memory VALUES (?, ?)", (h, datetime.now().isoformat()))
                return True
        return False

    def task_reply(self):
        logging.info("💬 بشوف إذا أحد يحتاج مساعدة أو استفسار...")
        query = "(\"كيف أستخدم AI\" OR #عمان_تتقدم OR \"أفضل هاتف\") -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=5, user_auth=True)
            if tweets.data:
                for t in tweets.data:
                    with sqlite3.connect(DB_FILE) as conn:
                        if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=?", (str(t.id),)).fetchone(): continue
                    
                    reply = self._safe_ai_call("خبير تقني وصديق للجميع.", f"رد بأسلوب ودي وسلس جداً كأنك تدردش مع صديقك: {t.text}")
                    if reply:
                        self.x.create_tweet(text=f"{reply[:280]}", in_reply_to_tweet_id=t.id)
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute("INSERT INTO tweet_history VALUES (?, ?)", (str(t.id), datetime.now().isoformat()))
                        return True
        except: pass
        return False

    def task_regular_post(self):
        logging.info("💡 وقت مشاركة نصيحة تقنية خفيفة...")
        topic = random.choice(TARGET_TOPICS)
        content = self._safe_ai_call(f"عطنا نصيحة أو ممارسة رهيبة في {topic}.", "دردشة تقنية")
        if content:
            self._publish_safe_thread(content, "💡 تدري؟ جرب هالحركة:\n")
            return True
        return False

    def run_strategy(self):
        # موازنة المهام: أولوية الخبر، ثم التفاعل مع الناس، ثم المحتوى العام
        if self.task_scoop(): return
        if random.random() > 0.5:
            if not self.task_reply(): self.task_regular_post()
        else:
            if not self.task_regular_post(): self.task_reply()

if __name__ == "__main__":
    bot = TechSupremeFriendly()
    bot.run_strategy()
