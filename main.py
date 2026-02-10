import os, sqlite3, logging, hashlib, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

# === 1. الهوية والبروتوكولات السيادية ===
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
DB_FILE = "sovereign_memory.db"

RTL_MARK = '\u200f'    # علامة اليمين لليسار
RTL_EMBED = '\u202b'   # إجبار التغليف من اليمين
RTL_POP = '\u202c'     # إغلاق التوجيه

# مصفوفة تقييم النخبوية
BASE_ELITE_SCORE = {
    "leak": 5, "exclusive": 5, "ai agent": 5, "benchmark": 4,
    "hands-on": 4, "chip": 4, "gpu": 3, "specs": 3, "linux": 3
}

# ساعات الذروة المبدئية (يمكن تعديلها لاحقاً ديناميكيًا)
PEAK_HOURS = [9,10,11,19,20,21,22]

class SovereignApexBotV104:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://venturebeat.com/feed/",
            "https://wccftech.com/feed/"
        ]

    # === 2. إدارة الذاكرة وقاعدة البيانات ===
    def _init_db(self):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")
            c.execute("""CREATE TABLE IF NOT EXISTS feedback (
                tweet_id TEXT PRIMARY KEY, reward REAL, likes INTEGER, retweets INTEGER, hour INTEGER
            )""")
            c.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # === 3. فلاتر الأمان والذكاء ===
    def _is_throttled(self, task, minutes):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            return r and datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    # === 4. Epsilon-Greedy Strategy ===
    def _decide_strategy(self, epsilon=0.2):
        """اختيار بين الاستغلال والاستكشاف"""
        return "EXPLORE" if random.random() < epsilon else "EXPLOIT"

    def _get_exploration_style(self):
        styles = [
            "أسلوب قصصي يربط التقنية بحياة الفرد اليومية.",
            "أسلوب مقارن بين أدوات أو تقنيات.",
            "أسلوب قائمة عملية (How-to) تبدأ غداً.",
            "أسلوب تخيلي مستقبلي (Impact after 5 years)."
        ]
        return random.choice(styles)

    # === 5. محرك الصياغة النخبوي ===
    def _brain(self, mission, context):
        charter = (
            "أنت خبير تقني خليجي نخبوي. لغتك خليجية بيضاء ذكية.\n"
            "ممنوع تبدأ بكلمات عامة. ابدأ مباشرة بشرارة.\n"
            "الهيكل: شرارة -> تحليل الفائدة -> 3 نقاط (💎⚡🛡️) -> سؤال نخبة.\n"
            "المصطلحات الإنجليزية بين أقواس. RTL Forced."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.0,
                messages=[{"role":"system","content":charter},
                          {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            content = res.choices[0].message.content.strip()
            return f"{RTL_EMBED}{RTL_MARK}{content}{RTL_POP}"
        except: return ""

    # === 6. تقييم الأداء السابق لتحديد أسلوب الأفضل ===
    def _get_optimal_style(self):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT reward, likes, retweets, tweet_id FROM feedback ORDER BY reward DESC LIMIT 1").fetchone()
        if r: return f"Analytical Style based on past ROI ({r[1]} likes, {r[2]} retweets)"
        return "Standard Analytical"

    # === 7. محرك النشر المعزز ===
    def post_elite_scoop(self):
        if self._is_throttled("post", 60): return

        strategy = self._decide_strategy()
        candidates = []

        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:10]:
                    pub_date = datetime(*e.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(hours=24): continue
                    score = sum(v for k, v in BASE_ELITE_SCORE.items() if k in e.title.lower())
                    if score >= 3: candidates.append(e)
            except: continue

        if not candidates: return

        # اختيار خبر عشوائي
        target = random.choice(candidates)
        h = hashlib.sha256(target.title.lower().strip().encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
            
            if strategy == "EXPLOIT":
                style_hint = self._get_optimal_style()
            else:
                style_hint = self._get_exploration_style()

            content = self._brain(f"صغ سكوب نخبوي بأسلوب {style_hint}", target.title)
            if content:
                try:
                    res = self.x.create_tweet(text=content)
                    tweet_id = res.data['id']
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    # حفظ مبدئي للتفاعل لاحقًا
                    c.execute("INSERT OR IGNORE INTO feedback (tweet_id, reward, likes, retweets, hour) VALUES (?,?,?,?,?)",
                              (tweet_id, 0.0, 0, 0, datetime.now().hour))
                    c.commit()
                    self._lock("post")
                    logging.info(f"🎯 Published [{strategy}] scoop: {target.title[:30]}")
                except Exception as e:
                    logging.error(f"X Error: {e}")

if __name__ == "__main__":
    bot = SovereignApexBotV104()
    bot.post_elite_scoop()
