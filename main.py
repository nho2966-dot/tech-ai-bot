import os, sqlite3, logging, hashlib, random, time, re
from datetime import datetime, timedelta
import tweepy, feedparser, requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# === 1. Governance & Environment ===
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
DB_FILE = "sovereign_memory.db"

# بروتوكولات إجبار المحاذاة من اليمين (RTL Protocols)
RTL_MARK = '\u200f'    # علامة اليمين لليسار
RTL_EMBED = '\u202b'   # إجبار التغليف من اليمين
RTL_POP = '\u202c'     # إنهاء التغليف

# مصفوفة تقييم المحتوى النخبوي
BASE_ELITE_SCORE = {
    "leak": 3, "exclusive": 3, "hands-on": 2, "benchmark": 2,
    "specs": 2, "chip": 2, "tool": 2, "update": 1,
    "ai agent": 3, "gpu": 2, "new feature": 2
}

# ساعات الذروة بتوقيت الخليج (لتحسين الوصول)
PEAK_HOURS = [9, 10, 11, 19, 20, 21, 22]

class SovereignApexBotV102_Final:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://www.macrumors.com/macrumors.xml",
            "https://venturebeat.com/feed/",
            "https://wccftech.com/feed/"
        ]
        self.reddit_feeds = [
            "https://www.reddit.com/r/technology/.rss",
            "https://www.reddit.com/r/Android/.rss",
            "https://www.reddit.com/r/apple/.rss"
        ]

    # === 2. Database & Persistence ===
    def _init_db(self):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS feedback (tweet_id TEXT PRIMARY KEY, reward REAL)")
            c.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # === 3. Intelligence & Safety ===
    def _is_throttled(self, task, minutes):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            return r and datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    def _brain(self, mission, context):
        """محرك الصياغة السيادي: خليجي، نخبوي، ومحاذاة RTL مضمونة"""
        charter = (
            "أنت خبير تقني خليجي نخبوي. لغتك (خليجية بيضاء) ذكية وحماسية.\n"
            "قاعدة ذهبية: ابدأ النص دائماً بكلمة عربية قوية. ممنوع البدء برموز أو إنجليزي.\n"
            "الهيكل المعتمد: شرارة حماسية -> متن انسيابي يوضح الفائدة للفرد -> 3 مواصفات (💎⚡🛡️) -> سؤال استراتيجي.\n"
            "المصطلحات الإنجليزية بين أقواس ( ). لا تهلوس."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.0,
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            content = res.choices[0].message.content.strip()
            # تغليف المحاذاة السيادي
            return f"{RTL_EMBED}{RTL_MARK}{content}{RTL_POP}"
        except: return ""

    # === 4. Content Engine ===
    def post_elite_scoop(self):
        # التحقق من وقت الذروة أو المهلة
        is_peak = datetime.now().hour in PEAK_HOURS
        wait_time = 45 if is_peak else 120
        if self._is_throttled("post", wait_time): return

        all_entries = []
        for src in (self.sources + self.reddit_feeds):
            try:
                feed = feedparser.parse(src)
                all_entries.extend(feed.entries[:5])
            except: continue

        candidates = []
        for e in all_entries:
            text = (e.title + getattr(e, 'description', '')).lower()
            score = sum(v for k, v in BASE_ELITE_SCORE.items() if re.search(rf"\b{k}\b", text))
            if score >= 3: candidates.append(e)

        if not candidates: return
        target = random.choice(candidates)
        h = hashlib.sha256(target.title.encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
            
            content = self._brain("صغ سكوب خليجي حماسي يركز على الفرد والإنتاجية التقنية.", target.title)
            if content:
                try:
                    self.x.create_tweet(text=content)
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info("🎯 Published Strategic Scoop.")
                except Exception as e: logging.error(f"X Error: {e}")

    def handle_mentions(self):
        if self._is_throttled("mentions", 10): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id)
            if not mentions.data: return
            with sqlite3.connect(DB_FILE) as c:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    
                    reply = self._brain("رد خليجي نخبوي ذكي ومختصر جداً.", t.text)
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        c.commit()
        except: pass

if __name__ == "__main__":
    bot = SovereignApexBotV102_Final()
    bot.handle_mentions()
    bot.post_elite_scoop()
