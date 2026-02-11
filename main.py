import os, sqlite3, logging, hashlib, re, json, time, random
import numpy as np
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CONFIG = {
    "DB": "sovereign_apex_v311.db",
    "PEAK_HOURS": [9,12,18,19,20,21,22],
    "COOLDOWN_SECONDS": 5400,
    "QUEUE_EXPIRY_DAYS": 2,
    "SIM_THRESHOLD": 0.88,
    "SILENT_THRESHOLD": 3.0,
    "DRY_RUN": False
}

RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

class SovereignApexV311:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://wccftech.com/feed/"
        ]

    def _init_db(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, embedding TEXT)")
            c.execute("""CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY, h TEXT UNIQUE, source TEXT, title TEXT, 
                content TEXT, media_url TEXT, media_type TEXT, score REAL, 
                status TEXT DEFAULT 'PENDING', created_at TEXT
            )""")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS performance (tweet_id TEXT PRIMARY KEY, hook_type TEXT, score REAL, created_at TEXT)")
            c.commit()

    def _init_clients(self):
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        auth = tweepy.OAuth1UserHandler(os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"), os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET"))
        self.api_v1 = tweepy.API(auth)
        self.x = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN"), consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"), access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"))

    # === AI CORE FUNCTIONS (Fixed) ===
    def _embedding(self, text):
        res = self.ai.embeddings.create(model="text-embedding-3-small", input=text)
        return np.array(res.data[0].embedding)

    def _cosine(self, a, b):
        return np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b))

    def _is_semantic_duplicate(self, emb):
        with sqlite3.connect(CONFIG["DB"]) as c:
            rows = c.execute("SELECT embedding FROM memory").fetchall()
        for r in rows:
            old = np.array(json.loads(r[0]))
            if self._cosine(emb, old) > CONFIG["SIM_THRESHOLD"]: return True
        return False

    def _brain(self, title, hook_style):
        charter = "أنت مستشار تقني خليجي نخبوي. لغتك (خليجية بيضاء رصينة). ركز على الفرد. المصطلحات بين أقواس ( )."
        hook_prompt = "اكتب افتتاحية قوية جداً" if hook_style == "A" else "اكتب سؤالاً استفزازياً للفضول"
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": charter},{"role": "user", "content": f"{hook_prompt} لهذا الخبر: {title}. ثم أتبعه بتحليل تقني عميق للفرد في 3 أسطر."}]
            )
            return f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"
        except: return ""

    def _ai_gate(self, title):
        prompt = f"هل هذا الخبر يهم المستخدم الفرد مباشرة؟ YES أو NO فقط:\n{title}"
        r = self.ai.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", temperature=0.1, messages=[{"role":"user","content":prompt}])
        return "YES" in r.choices[0].message.content.upper()

    def _score(self, title, source):
        # منطق تقييم بسيط لضمان جودة المحتوى
        return 5.0 if any(x in title.lower() for x in ["ai", "chip", "update", "leak"]) else 2.0

    # === LOGIC & OPERATIONS ===
    def fetch(self):
        for src in self.sources:
            feed = feedparser.parse(src)
            for e in feed.entries[:5]:
                title = e.title.strip()
                if not self._ai_gate(title): continue
                
                h = hashlib.sha256(title.encode()).hexdigest()
                emb = self._embedding(title)
                if self._is_semantic_duplicate(emb): continue

                m_url, m_type = self._get_media(e)
                with sqlite3.connect(CONFIG["DB"]) as c:
                    c.execute("INSERT OR IGNORE INTO queue (h,source,title,media_url,media_type,score,created_at) VALUES (?,?,?,?,?,?,?)",
                              (h, src, title, m_url, m_type, self._score(title, src), datetime.now().isoformat()))
                    c.execute("INSERT OR IGNORE INTO memory (h, embedding) VALUES (?,?)", (h, json.dumps(emb.tolist())))
                    c.commit()

    def _get_media(self, entry):
        return (None, None) # يمكن تطويره لاحقاً لجلب الصور

    def _can_publish(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            r = c.execute("SELECT value FROM meta WHERE key='last_publish'").fetchone()
        if not r: return True
        return (datetime.now() - datetime.fromisoformat(r[0])).total_seconds() > CONFIG["COOLDOWN_SECONDS"]

    def _best_hook_style(self):
        return "A" # يمكن تطويره بناءً على جدول performance

    def dispatch(self):
        if not self._can_publish(): return
        with sqlite3.connect(CONFIG["DB"]) as c:
            row = c.execute("SELECT id,h,title,media_url,media_type FROM queue WHERE status='PENDING' ORDER BY score DESC LIMIT 1").fetchone()
        if not row: return
        q_id, h, title, m_url, m_type = row
        content = self._brain(title, self._best_hook_style())
        try:
            self.x.create_tweet(text=content)
            with sqlite3.connect(CONFIG["DB"]) as c:
                c.execute("UPDATE queue SET status='PUBLISHED' WHERE id=?", (q_id,))
                c.execute("REPLACE INTO meta VALUES ('last_publish',?)", (datetime.now().isoformat(),))
                c.commit()
            print(f"✅ Published: {title}")
        except Exception as e: print(f"❌ Error: {e}")

    def run(self):
        self.fetch()
        self.dispatch()

if __name__ == "__main__":
    SovereignApexV311().run()
