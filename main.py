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
RTL_MARK = '\u200f'

# Elite Scoring Matrix
BASE_ELITE_SCORE = {
    "leak": 3, "exclusive": 3, "hands-on": 2, "benchmark": 2,
    "specs": 2, "chip": 2, "tool": 2, "update": 1,
    "ai agent": 3, "gpu": 2, "new feature": 2
}

class SovereignApexBotV101:
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

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")
            c.execute("""CREATE TABLE IF NOT EXISTS feedback (
                tweet_id TEXT PRIMARY KEY, topic TEXT, style TEXT, reward REAL, hour INTEGER, age_hours REAL)""")
            c.execute("CREATE TABLE IF NOT EXISTS user_profile (user_id TEXT PRIMARY KEY, level TEXT)")
            c.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_throttled(self, task, minutes):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            return r and datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    def _brain(self, mission, context):
        charter = (
            f"{RTL_MARK}أنت مستشار تقني خليجي نخبوي. خليجية بيضاء، صفر هلوسة.\n"
            "1. Hook قوي.\n2. فائدة فردية مباشرة.\n3. مواصفات (💎⚡🛡️).\n4. سؤال ختامي.\n"
            "الإنجليزية بين أقواس، محاذاة RTL."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.0,
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            return res.choices[0].message.content.strip()
        except: return ""

    def _update_feedback(self):
        try:
            tweets = self.x.get_users_tweets(id=self.bot_id, max_results=10, tweet_fields=['public_metrics','created_at'])
            if not tweets.data: return
            with sqlite3.connect(DB_FILE) as c:
                for t in tweets.data:
                    h = hashlib.sha256(t.text[:100].encode()).hexdigest()
                    m = t.public_metrics
                    reward = m['like_count'] + 2*m['reply_count'] + 3*m['retweet_count']
                    c.execute("INSERT OR REPLACE INTO feedback (tweet_id, reward) VALUES (?,?)", (h, reward))
                c.commit()
        except: pass

    def _get_optimal_style(self, topic):
        return "Narrative Expert"

    def post_elite_scoop(self):
        if self._is_throttled("post", 60): return
        
        all_entries = []
        for src in (self.sources + self.reddit_feeds):
            try:
                feed = feedparser.parse(src)
                all_entries.extend(feed.entries[:3])
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
            
            content = self._brain("صغ سكوب خليجي نخبوي يركز على فائدة الفرد القصوى.", target.title)
            if content:
                try:
                    self.x.create_tweet(text=f"{RTL_MARK}{content}")
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info("🚀 Published successfully.")
                except Exception as e: logging.error(f"X Error: {e}")

    def handle_mentions(self):
        if self._is_throttled("mentions", 15): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id)
            if not mentions.data: return
            with sqlite3.connect(DB_FILE) as c:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    reply = self._brain("رد نخبوي خليجي بيضاء مختصر ومفيد.", t.text)
                    if reply:
                        self.x.create_tweet(text=f"{RTL_MARK}{reply}", in_reply_to_tweet_id=t.id)
                        c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        c.commit()
        except: pass

if __name__ == "__main__":
    bot = SovereignApexBotV101()
    bot.handle_mentions()
    bot.post_elite_scoop()
