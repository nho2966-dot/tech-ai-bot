import os, sqlite3, logging, hashlib, time, random, textwrap
from datetime import datetime
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. الإعدادات والذاكرة السيادية ---
load_dotenv()
DB_FILE = "tech_om_enterprise_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# المواضيع الـ 10 المختارة بعناية للثورة الرابعة
TARGET_TOPICS = [
    "أدوات الذكاء الاصطناعي (AI Tools)", "إنتاجية الأفراد الرقمية", 
    "الأمن السيبراني الشخصي", "التقنيات المالية (FinTech)", 
    "الأتمتة الشخصية (No-Code)", "هندسة الأوامر (Prompt Engineering)", 
    "تحليل البيانات الضخمة", "الواقع المعزز (AR)", "الألعاب السحابية", "السبق التقني"
]

NEWS_SOURCES = ["https://www.theverge.com/rss/index.xml", "https://www.wired.com/feed/rss"]
CTA_MAP = {"ai_tool": "📌 احفظ الأداة.", "info": "🔁 أعد التغريد.", "scoop": "🚀 تابع للحصريات.", "quiz": "💬 شاركنا رأيك."}
STYLE_MODES = ["3 نقاط قصيرة جداً.", "نقطتان مع مثال عملي.", "نقطة مركزة + تحذير تقني."]
TRUSTED_KEYWORDS = ["official", "announced", "released", "launch", "update", "new"]

class TechSovereignMain:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.ai_calls = 0
        self.MAX_AI_CALLS = 25
        self.last_ai_reset = datetime.now().date()

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS content_memory 
                         (h TEXT PRIMARY KEY, h_link TEXT, type TEXT, topic TEXT, monetizable INTEGER DEFAULT 0, dt TEXT)""")
            conn.execute("CREATE TABLE IF NOT EXISTS tweet_history (tweet_id TEXT PRIMARY KEY, text_hash TEXT, dt TEXT)")
            conn.execute("""CREATE TABLE IF NOT EXISTS performance 
                         (tweet_id TEXT PRIMARY KEY, type TEXT, likes INTEGER, retweets INTEGER, replies INTEGER, dt TEXT)""")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # --- 2. محرك الذكاء (Zero Hallucination) ---
    def _safe_ai_call(self, sys_p, user_p):
        if datetime.now().date() != self.last_ai_reset:
            self.ai_calls = 0
            self.last_ai_reset = datetime.now().date()
        if self.ai_calls >= self.MAX_AI_CALLS: return None

        style = random.choice(STYLE_MODES)
        STRICT_SYSTEM = (sys_p + f"\n[صفر هلوسة]. {style} ابدأ بجملة Claim قوية. اذكر المصدر بالاسم.")

        try:
            self.ai_calls += 1
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": STRICT_SYSTEM}, {"role": "user", "content": user_p}],
                temperature=0.15
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}"); return None

    # --- 3. نظام الردود العميقة (Deep Expert Replies) ---
    def task_expert_reply(self):
        query = "(\"كيف أستخدم AI\" OR \"مشكلة تقنية\" OR #عمان_تتقدم) -is:retweet"
        try:
            tweets = self.x.search_recent_tweets(query=query, max_results=5, user_auth=True)
            if not tweets or not tweets.data: return False
            for t in tweets.data:
                text_hash = hashlib.sha256(t.text.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM tweet_history WHERE tweet_id=? OR text_hash=?", (str(t.id), text_hash)).fetchone(): continue
                
                # الرد العميق: تحليل المشكلة وتقديم حل في خطوة واحدة
                reply = self._safe_ai_call("خبير حلول تقنية.", f"حلل بعمق ورد بخطوة عملية واحدة أو أداة واحدة فقط على: {t.text}")
                if reply:
                    final_reply = reply.strip() + "\n\n— Tech Insight"
                    self.x.create_tweet(text=final_reply[:280], in_reply_to_tweet_id=t.id)
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO tweet_history VALUES (?, ?, ?)", (str(t.id), text_hash, datetime.now().isoformat()))
                    logging.info(f"✅ تم الرد بعمق على: {t.id}")
                    return True
        except Exception as e:
            logging.error(f"Reply Task Failed: {e}"); return False
        return False

    # --- 4. محرك النشر والتعلم (Decision Engine) ---
    def task_scoop_and_content(self):
        now_hour = datetime.now().hour
        if now_hour < 9 or now_hour > 23: return False

        # جلب الأوزان الديناميكية من الأداء السابق
        weights_dict = {"scoop": 2, "ai_tool": 3, "info": 4, "quiz": 1}
        task_type = random.choices(list(weights_dict.keys()), weights=list(weights_dict.values()))[0]
        
        with sqlite3.connect(DB_FILE) as conn:
            last_t = conn.execute("SELECT topic FROM content_memory ORDER BY dt DESC LIMIT 1").fetchone()
            topic = random.choice([t for t in TARGET_TOPICS if t != (last_t[0] if last_t else "")])

        h_link, content = "none", None
        if task_type == "scoop":
            feed = feedparser.parse(random.choice(NEWS_SOURCES))
            for entry in feed.entries[:5]:
                if not any(k in entry.title.lower() for k in TRUSTED_KEYWORDS): continue
                h_link = hashlib.sha256(entry.link.encode()).hexdigest()
                with sqlite3.connect(DB_FILE) as conn:
                    if conn.execute("SELECT 1 FROM content_memory WHERE h_link=?", (h_link,)).fetchone(): continue
                content = self._safe_ai_call("محلل أخبار عاجلة.", f"لخص هذا الخبر التقني: {entry.title} - المصدر: {entry.link}")
                break
        else:
            p_map = {"info": f"نصيحة تقنية في {topic}.", "ai_tool": f"أداة AI ثورية في {topic}.", "quiz": f"سؤال تفاعلي ذكي في {topic}."}
            content = self._safe_ai_call(f"خبير {topic}.", p_map[task_type])

        if content:
            h = hashlib.sha256(content.encode()).hexdigest()
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO content_memory VALUES (?, ?, ?, ?, ?, ?)", 
                             (h, h_link, task_type, topic, (1 if task_type=="ai_tool" else 0), datetime.now().isoformat()))
            self._publish_thread(content, task_type)
            return True
        return False

    def _publish_thread(self, content, task_type):
        chunks = textwrap.wrap(content, width=250, break_long_words=False)
        prev_id, first_id = None, None
        for i, chunk in enumerate(chunks):
            if i == len(chunks)-1: chunk += f"\n\n{CTA_MAP.get(task_type, '')}"
            try:
                tweet = self.x.create_tweet(text=chunk, in_reply_to_tweet_id=prev_id)
                prev_id = tweet.data['id']
                if i == 0: first_id = prev_id
                time.sleep(120)
            except: break
        if first_id:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT OR IGNORE INTO performance VALUES (?, ?, 0, 0, 0, ?)", (str(first_id), task_type, datetime.now().isoformat()))

    def run_strategy(self):
        # 1. الردود أولاً للنمو 2. المحتوى ثانياً للسيادة
        if not self.task_expert_reply():
            self.task_scoop_and_content()

if __name__ == "__main__":
    bot = TechSovereignMain()
    bot.run_strategy()
