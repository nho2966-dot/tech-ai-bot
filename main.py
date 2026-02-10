import os, sqlite3, logging, hashlib, random, time, re
from datetime import datetime, timedelta
import tweepy, feedparser, requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# === 1. Governance & Environmental Setup ===
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
DB_FILE = "sovereign_memory.db"
RTL_MARK = '\u200f'  # رمز إجبار المحاذاة من اليمين لليسار

BASE_ELITE_SCORE = {
    "leak": 3, "exclusive": 3, "hands-on": 2, "benchmark": 2,
    "specs": 2, "chip": 2, "tool": 2, "update": 1,
    "ai agent": 3, "gpu": 2, "new feature": 2
}

class SovereignApexBotV100Plus:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://www.macrumors.com/macrumors.xml",
            "https://venturebeat.com/feed/"
        ]

    # === 2. Core Database & Intelligence ===
    def _init_db(self):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS context_memory (topic TEXT, hour INTEGER, style TEXT, strategy TEXT, reward REAL)")
            c.execute("CREATE TABLE IF NOT EXISTS user_profile (user_id TEXT PRIMARY KEY, level TEXT)")
            c.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # === 3. Safety & Grounding Guards ===
    def _is_throttled(self, task, minutes):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            return r and datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    # === 4. Advanced AI Brain (Zero Hallucination) ===
    def _brain(self, mission, context):
        charter = (
            f"أنت مستشار تقني خليجي نخبوي. ابدأ التغريدة دائماً بـ 'خطّاف' (Hook) مثير يمس الفرد مباشرة.\n"
            "اللغة: خليجية بيضاء رصينة. اتجاه النص: من اليمين لليسار.\n"
            "الشرط الحرج: التزم فقط بالحقائق المذكورة حرفياً. لا تخترع أسعاراً أو مواعيد.\n"
            "الهيكل: خطّاف -> عنوان السكوب -> ليش يهمك (الفائدة المضافة) -> نقاط المواصفات -> سؤال للنخبة."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.0,
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            content = res.choices[0].message.content.strip()
            # حقن رمز الـ RTL لضمان المحاذاة في X
            return f"{RTL_MARK}{content}"
        except: return ""

    # === 5. Dynamic Content Logic ===
    def post_elite_scoop(self):
        if self._is_throttled("post", 100): return
        
        candidates = []
        for src in self.sources:
            feed = feedparser.parse(src)
            for e in feed.entries[:5]:
                text = (e.title + e.description).lower()
                score = sum(v for k, v in BASE_ELITE_SCORE.items() if re.search(rf"\b{k}\b", text))
                if score >= 3 and len(e.description) > 100:
                    candidates.append(e)

        if not candidates: return
        target = random.choice(candidates)
        h = hashlib.sha256((target.title + target.description[:100]).encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return

            content = self._brain("صغ سكوب نخبوي بأسلوب يركز على الفرد والإنتاجية.", f"{target.title}\n{target.description}")
            if content:
                try:
                    self.x.create_tweet(text=content)
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info("🎯 Published with RTL alignment and Hook.")
                except Exception as e: logging.error(f"X Error: {e}")

    def handle_mentions(self):
        if self._is_throttled("mentions", 15): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, expansions=['author_id', 'entities'])
            if not mentions.data: return
            with sqlite3.connect(DB_FILE) as c:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    
                    reply = self._brain("رد تقني خليجي نخبوي ومختصر ومحاذى لليمين.", t.text)
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        c.commit()
        except: pass

if __name__ == "__main__":
    bot = SovereignApexBotV100Plus()
    bot.handle_mentions()
    bot.post_elite_scoop()
