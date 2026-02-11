import os, sqlite3, logging, hashlib, re, json, time, random
import numpy as np
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI

# ================= CONFIG =================
load_dotenv()

CONFIG = {
    "DB": "sovereign_apex_v310.db",
    "PEAK_HOURS": [9,12,18,19,20,21,22],
    "COOLDOWN_SECONDS": 5400, # ساعة ونصف بين التغريدات
    "QUEUE_EXPIRY_DAYS": 2,
    "SIM_THRESHOLD": 0.88,
    "SILENT_THRESHOLD": 3.0,
    "DRY_RUN": False
}

# التحكم بالمحاذاة
RTL_EMBED = '\u202b'
RTL_MARK = '\u200f'
RTL_POP = '\u202c'

# ================= BOT CLASS =================
class SovereignApexV310:

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
            c.execute("CREATE TABLE IF NOT EXISTS leaderboard (handle TEXT PRIMARY KEY, points INTEGER DEFAULT 0)")
            c.commit()

    def _init_clients(self):
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        auth = tweepy.OAuth1UserHandler(os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"), os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET"))
        self.api_v1 = tweepy.API(auth)
        self.x = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN"), consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"), access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"))

    # ================= AI LOGIC (The Elite Brain) =================
    def _brain(self, title, hook_style):
        charter = (
            "أنت مستشار تقني خليجي نخبوي. لغتك (خليجية بيضاء رصينة).\n"
            "ركز على مصلحة الفرد وممارسات الثورة الصناعية 4.0.\n"
            "الممنوعات: (يا رفاق، تقنية، يعد، يمثل، خبر، إعلان، مميزات، كتير، شو).\n"
            "المصطلحات التقنية بين أقواس ( ). المحاذاة RTL."
        )
        
        hook_prompt = "اكتب افتتاحية قوية جداً" if hook_style == "A" else "اكتب سؤالاً استفزازياً للفضول"
        
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": charter},
                    {"role": "user", "content": f"{hook_prompt} لهذا الخبر: {title}. ثم أتبعه بتحليل تقني عميق للفرد في 3 أسطر."}
                ]
            )
            content = res.choices[0].message.content.strip()
            return f"{RTL_EMBED}{RTL_MARK}{content}{RTL_POP}"
        except: return ""

    def _ai_gate(self, title):
        """حارس البوابة: يرفض أخبار الشركات ويقبل ما يهم الفرد فقط"""
        prompt = f"هل هذا الخبر يهم المستخدم الفرد مباشرة (جهاز جديد، تحديث، تسريب، أداة ذكاء اصطناعي) وليس خبراً مؤسسياً جافاً؟ أجب YES أو NO فقط:\n{title}"
        r = self.ai.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", temperature=0.1, messages=[{"role":"user","content":prompt}])
        return "YES" in r.choices[0].message.content.upper()

    # ================= MEDIA & FETCH =================
    def _get_media(self, entry):
        v_url, i_url = None, None
        if 'links' in entry:
            for l in entry.links:
                if 'video' in l.get('type', ''): v_url = l.href
                if 'image' in l.get('type', ''): i_url = l.href
        return (v_url, "video") if v_url else (i_url, "image")

    def fetch(self):
        for src in self.sources:
            feed = feedparser.parse(src)
            for e in feed.entries[:8]:
                title = e.title.strip()
                if not self._ai_gate(title): continue

                h = hashlib.sha256(title.encode()).hexdigest()
                # التحقق الدلالي (Semantic Check)
                emb = self._embedding(title)
                if self._is_semantic_duplicate(emb): continue

                m_url, m_type = self._get_media(e)
                score = self._score(title, src)
                
                with sqlite3.connect(CONFIG["DB"]) as c:
                    c.execute("INSERT OR IGNORE INTO queue (h,source,title,media_url,media_type,score,created_at) VALUES (?,?,?,?,?,?,?)",
                              (h, src, title, m_url, m_type, score, datetime.now().isoformat()))
                    c.execute("INSERT OR IGNORE INTO memory (h, embedding) VALUES (?,?)", (h, json.dumps(emb.tolist())))
                    c.commit()

    # ================= OPERATIONS =================
    def dispatch(self):
        if datetime.now().hour not in CONFIG["PEAK_HOURS"]: return
        if not self._can_publish(): return

        with sqlite3.connect(CONFIG["DB"]) as c:
            row = c.execute("SELECT id,h,title,media_url,media_type FROM queue WHERE status='PENDING' ORDER BY score DESC LIMIT 1").fetchone()
        
        if not row: return
        q_id, h, title, m_url, m_type = row
        
        hook_style = self._best_hook_style()
        content = self._brain(title, hook_style)
        
        # رفع الميديا (صور/فيديو)
        media_ids = self._upload_media(m_url, m_type, h)

        try:
            tweet = self.x.create_tweet(text=content, media_ids=media_ids if media_ids else None)
            with sqlite3.connect(CONFIG["DB"]) as c:
                c.execute("UPDATE queue SET status='PUBLISHED', content=? WHERE id=?", (content, q_id))
                c.execute("REPLACE INTO meta VALUES ('last_publish',?)", (datetime.now().isoformat(),))
                c.execute("INSERT INTO performance (tweet_id,hook_type,created_at) VALUES (?,?,?)", (tweet.data["id"], hook_style, datetime.now().isoformat()))
                c.commit()
            logging.info(f"✅ تم النشر التكيفي: {title[:30]}")
        except Exception as e: logging.error(f"❌ X Error: {e}")

    def _upload_media(self, url, m_type, h):
        if not url: return None
        try:
            path = f"temp_{h}.mp4" if m_type == "video" else f"temp_{h}.jpg"
            with requests.get(url, stream=True) as r:
                with open(path, "wb") as f:
                    for chunk in r.iter_content(8192): f.write(chunk)
            media = self.api_v1.media_upload(path, media_category='tweet_video' if m_type=="video" else 'tweet_image')
            if m_type == "video": time.sleep(15) # انتظار المعالجة
            os.remove(path)
            return [media.media_id]
        except: return None

    # ================= CONTESTS (Weekly Thursday) =================
    def run_weekly_contest(self):
        now = datetime.now()
        if now.strftime("%A") == "Thursday" and now.hour == 20:
            h = hashlib.sha256(f"contest_{now.strftime('%Y%W')}".encode()).hexdigest()
            with sqlite3.connect(CONFIG["DB"]) as c:
                if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
                
                q = self._brain("ابتكر تحدي تقني نُخبوي للأذكياء عن مستقبل AI الشخصي.", "B")
                contest_text = f"🏆 【تحدي السيادة للأذكياء】\n\n{q}\n\n🎁 الجائزة: 'وسام التميز' + تتويج حسابك كخبير للأسبوع! 💎"
                self.x.create_tweet(text=contest_text)
                c.execute("INSERT INTO memory (h) VALUES (?)", (h,))
                c.commit()

    # ================= MAIN RUN =================
    def run(self):
        self.fetch()
        self.dispatch()
        self.run_weekly_contest()
        # دالة تحديث الأداء (موجودة في كودك V300)
        # self.update_performance()

if __name__ == "__main__":
    bot = SovereignApexV310()
    bot.run()
