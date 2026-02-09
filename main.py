import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignZenithV77:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss",
            "https://arstechnica.com/feed/"
        ]
        self.charter = (
            "أنت المستشار التقني الخليجي الأعلى. لغتك نُخبوية بيضاء.\n"
            "التركيز: الثورة الصناعية الرابعة، أدوات AI العملية، والسيادة الرقمية.\n"
            "الشروط: مصطلحات إنجليزية بين قوسين، لا تكرار، لا هلوسة."
        )

    def _init_db(self):
        with sqlite3.connect("sovereign_memory.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _brain(self, prompt, context=""):
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.1
            ).choices[0].message.content.strip()
            return res
        except: return ""

    def _is_throttled(self, task, minutes):
        with sqlite3.connect("sovereign_memory.db") as conn:
            res = conn.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            if res and datetime.now() < datetime.fromisoformat(res[0]) + timedelta(minutes=minutes):
                return True
        return False

    def handle_mentions(self):
        logging.info("🔎 Checking mentions (Selective Mode)...")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, max_results=5)
            if not mentions.data: return
            with sqlite3.connect("sovereign_memory.db") as conn:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue
                    reply = self._brain(f"رد بتحليل ذكي: {t.text}")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        conn.commit()
                        time.sleep(120)
        except tweepy.errors.TooManyRequests: logging.warning("⚠️ X Rate Limit - Mentions")

    def post_content(self):
        """نظام المحتوى المتناوب: مرة خبر، ومرة تفاعل (AI Tool/Quiz)"""
        if self._is_throttled("main_post", 110): return
        
        mode = random.choice(["SCOOP", "ENGAGEMENT"])
        logging.info(f"🚀 Content Mode: {mode}")

        with sqlite3.connect("sovereign_memory.db") as conn:
            if mode == "SCOOP":
                all_entries = []
                for url in self.sources:
                    feed = feedparser.parse(url)
                    for e in feed.entries[:3]:
                        if (datetime.now() - datetime(*e.published_parsed[:6])) <= timedelta(hours=36):
                            all_entries.append(e)
                if all_entries:
                    entry = random.choice(all_entries)
                    h = hashlib.sha256(entry.title.encode()).hexdigest()
                    if not conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        txt = self._brain("صغ ثريداً استراتيجياً قصيراً عن هذا الخبر.", f"{entry.title}\n{entry.description}")
                        if txt:
                            tweets = [t.strip() for t in txt.split("---") if len(t.strip()) > 5]
                            p_id = None
                            for tw in tweets:
                                res = self.x.create_tweet(text=tw, in_reply_to_tweet_id=p_id)
                                p_id = res.data['id']
                                time.sleep(60)
                            conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "SCOOP", datetime.now().isoformat()))

            else: # ENGAGEMENT MODE
                prompt = "اطرح سؤالاً تقنياً عميقاً أو اشرح أداة AI عملية للأفراد (Industry 4.0)."
                txt = self._brain(prompt)
                if txt:
                    self.x.create_tweet(text=txt)
                    conn.execute("INSERT INTO memory VALUES (?,?,?)", (hashlib.sha256(txt[:20].encode()).hexdigest(), "ENGAGE", datetime.now().isoformat()))

            conn.execute("INSERT OR REPLACE INTO throttle VALUES ('main_post', ?)", (datetime.now().isoformat(),))
            conn.commit()

if __name__ == "__main__":
    bot = SovereignZenithV77()
    bot.handle_mentions()
    bot.post_content()
