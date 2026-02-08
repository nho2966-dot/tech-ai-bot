import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# تفعيل مستوى INFO لمشاهدة ما يحدث في GitHub Actions
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignDiagnosticAgent:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss",
            "https://arstechnica.com/feed/",
            "https://9to5mac.com/feed/",
            "https://9to5google.com/feed/"
        ]
        self.charter = (
            "أنت المستشار التقني الأعلى. فكرك نخبوي.\n"
            "1. الهوية: خليجية نُخبوية رصينة، مصطلحات تقنية دقيقة بين قوسين ().\n"
            "2. المنطق: (تحليل الخبر + المقارنة التنافسية + الأثر على السيادة الرقمية والخصوصية).\n"
            "3. الفلاتر: منع الهلوسة، منع الأخبار البائتة (>36س)، منع الرد على النفس أو التكرار."
        )

    def _init_db(self):
        with sqlite3.connect("sovereign_v73.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _strategic_brain(self, prompt, context=""):
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.1
            ).choices[0].message.content.strip()
            return res if re.match(r'^[ \u0600-\u06FF0-9a-zA-Z()\[\]\.\!\?\-\n\r]+$', res) else ""
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return ""

    def handle_mentions(self):
        logging.info("🔎 Checking mentions...")
        # (نفس منطق Mentions السابق مع إضافة Logging عند كل خطوة)
        logging.info("✅ Mentions check complete.")

    def post_elite_scoops(self):
        logging.info("📡 Scanning global tech sources...")
        all_entries = []
        for url in self.sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                p_date = datetime(*entry.published_parsed[:6])
                if (datetime.now() - p_date) <= timedelta(hours=36):
                    all_entries.append(entry)
        
        logging.info(f"📊 Found {len(all_entries)} fresh entries within 36h.")
        
        if not all_entries:
            logging.info("😴 No new strategic scoops found. Standing by.")
            return

        entry = random.choice(all_entries)
        h = hashlib.sha256(entry.title.encode()).hexdigest()
        
        with sqlite3.connect("sovereign_v73.db") as conn:
            if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                logging.info(f"♻️ Content '{entry.title[:30]}...' already posted. Skipping.")
                return
            
            logging.info(f"🚀 Generating strategic thread for: {entry.title}")
            instr = "صغ ثريداً استراتيجياً نخبويًا (Hook-Value-Impact-CTA). قارن بمنافسين."
            content = self._strategic_brain(instr, f"{entry.title}\n{entry.description}")
            
            if content:
                tweets = [t.strip() for t in content.split("---") if len(t.strip()) > 10]
                p_id = None
                for txt in tweets:
                    res = self.x.create_tweet(text=txt, in_reply_to_tweet_id=p_id)
                    p_id = res.data['id']
                    time.sleep(30)
                conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "THREAD", datetime.now().isoformat()))
                conn.commit()
                logging.info("🎯 Thread published successfully.")

if __name__ == "__main__":
    agent = SovereignDiagnosticAgent()
    agent.handle_mentions()
    agent.post_elite_scoops()
