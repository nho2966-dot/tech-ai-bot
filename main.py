import os, sqlite3, logging, hashlib, re, json, time, random
import numpy as np
from datetime import datetime
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# الإعدادات الجوهرية
CONFIG = {
    "DB": "sovereign_apex_v311.db",
    "COOLDOWN_SECONDS": 5400,
    "SIM_THRESHOLD": 0.88,
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
                status TEXT DEFAULT 'PENDING', created_at TEXT
            )""")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.commit()

    def _init_clients(self):
        # OpenRouter للتفكير والتحليل
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        # X API للنشر
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # وظيفة التشفير الدلالي (التي كانت مفقودة)
    def _embedding(self, text):
        try:
            res = self.ai.embeddings.create(model="text-embedding-3-small", input=text)
            return np.array(res.data[0].embedding)
        except:
            return np.zeros(1536) # fallback

    def _cosine(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _is_semantic_duplicate(self, emb):
        with sqlite3.connect(CONFIG["DB"]) as c:
            rows = c.execute("SELECT embedding FROM memory").fetchall()
        for r in rows:
            old_emb = np.array(json.loads(r[0]))
            if self._cosine(emb, old_emb) > CONFIG["SIM_THRESHOLD"]:
                return True
        return False

    def _ai_gate(self, title):
        prompt = f"هل هذا الخبر يهم الفرد تقنياً؟ YES/NO فقط: {title}"
        r = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        return "YES" in r.choices[0].message.content.upper()

    def _brain(self, title):
        prompt = f"حلل هذا الخبر للفرد بلهجة خليجية بيضاء نخبويّة (بدون هاشتاقات): {title}"
        res = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "system", "content": "أنت مستشار تقني متخصص في الثورة الصناعية الرابعة."},
                      {"role": "user", "content": prompt}]
        )
        return f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"

    def fetch(self):
        for src in self.sources:
            feed = feedparser.parse(src)
            for e in feed.entries[:5]:
                title = e.title.strip()
                h = hashlib.sha256(title.encode()).hexdigest()
                
                # فحص الفلترة والذكاء الاصطناعي
                if not self._ai_gate(title): continue
                
                emb = self._embedding(title)
                if self._is_semantic_duplicate(emb): continue

                with sqlite3.connect(CONFIG["DB"]) as c:
                    c.execute("INSERT OR IGNORE INTO queue (h, source, title, created_at) VALUES (?,?,?,?)",
                              (h, src, title, datetime.now().isoformat()))
                    c.execute("INSERT OR IGNORE INTO memory (h, embedding) VALUES (?,?)", 
                              (h, json.dumps(emb.tolist())))
                    c.commit()

    def dispatch(self):
        # فحص وقت التهدئة (Cooldown)
        with sqlite3.connect(CONFIG["DB"]) as c:
            last = c.execute("SELECT value FROM meta WHERE key='last_publish'").fetchone()
            if last and (datetime.now() - datetime.fromisoformat(last[0])).total_seconds() < CONFIG["COOLDOWN_SECONDS"]:
                return

            row = c.execute("SELECT id, title FROM queue WHERE status='PENDING' LIMIT 1").fetchone()
            if not row: return
            
            q_id, title = row
            content = self._brain(title)
            
            try:
                self.x.create_tweet(text=content)
                c.execute("UPDATE queue SET status='PUBLISHED' WHERE id=?", (q_id,))
                c.execute("REPLACE INTO meta VALUES ('last_publish',?)", (datetime.now().isoformat(),))
                c.commit()
                print(f"✅ تم النشر: {title}")
            except Exception as e:
                print(f"❌ خطأ في النشر: {e}")

    def run(self):
        self.fetch()
        self.dispatch()

if __name__ == "__main__":
    SovereignApexV311().run()
