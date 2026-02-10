import os, sqlite3, logging, hashlib, time, random
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignResilientV86:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        
        # رادار النخبة العالمي
        self.elite_sources = [
            "https://www.bloomberg.com/technology/rss",
            "https://9to5mac.com/feed/",
            "https://wccftech.com/feed/",
            "https://www.wired.com/feed/rss",
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/",
            "https://www.digitimes.com/rss/daily.xml"
        ]

    def _init_db(self):
        with sqlite3.connect("sovereign_memory.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _strategic_brain(self, prompt, context=""):
        try:
            charter = (
                "أنت مستشار تقني نُخبوي خليجي. لغتك (خليجية بيضاء رصينة).\n"
                "الالتزام الصارم بالحقائق والأرقام. ممنوع الهلوسة.\n"
                "المصطلحات الإنجليزية بين أقواس (). الهيكل: مقدمة، نقاط مواصفات، تفاصيل، سؤال."
            )
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": charter}, 
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

    def post_elite_content(self):
        """نشر السكوبات بتنسيق (جوال ترامب) مع معالجة أخطاء التكرار"""
        if self._is_throttled("main_post", 110): return
        
        logging.info("📡 Scanning for fresh global scoops...")
        all_entries = []
        for url in self.elite_sources:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                try:
                    p_date = datetime(*e.published_parsed[:6])
                    if (datetime.now() - p_date) <= timedelta(hours=24):
                        all_entries.append(e)
                except: continue

        if not all_entries: return
        random.shuffle(all_entries)

        for entry in all_entries:
            h = hashlib.sha256(entry.title.encode()).hexdigest()
            with sqlite3.connect("sovereign_memory.db") as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                
                prompt = "صغ سكوب صحفي نُخبوي خليجي عن هذا الخبر بتنسيق المواصفات التقنية الكاملة."
                content = self._strategic_brain(prompt, f"{entry.title}\n{entry.description}")
                
                if content and len(content) > 150:
                    try:
                        self.x.create_tweet(text=content)
                        # استخدام INSERT OR IGNORE لتفادي الـ IntegrityError نهائياً
                        conn.execute("INSERT OR IGNORE INTO memory VALUES (?,?,?)", (h, "SCOOP", datetime.now().isoformat()))
                        conn.execute("INSERT OR REPLACE INTO throttle VALUES ('main_post', ?)", (datetime.now().isoformat(),))
                        conn.commit()
                        logging.info("🎯 Elite Scoop Published.")
                        return 
                    except Exception as e:
                        logging.error(f"Tweet Error: {e}")

    def handle_mentions(self):
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, max_results=5)
            if not mentions or not mentions.data: return
            with sqlite3.connect("sovereign_memory.db") as conn:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue
                    reply = self._strategic_brain(f"رد بتحليل ذكي: {t.text}")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        conn.execute("INSERT OR IGNORE INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        conn.commit()
                        time.sleep(120)
        except: pass

if __name__ == "__main__":
    bot = SovereignResilientV86()
    bot.handle_mentions()
    bot.post_elite_content()
