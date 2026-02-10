import os, sqlite3, logging, hashlib, random, re
from datetime import datetime, timedelta
import tweepy, feedparser, requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# === 1. الإعدادات والتحكم بالبيئة ===
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
DB_FILE = "sovereign_memory.db"

# بروتوكولات إجبار المحاذاة من اليمين (RTL Force)
RTL_MARK = '\u200f'    # علامة اليمين لليسار
RTL_EMBED = '\u202b'   # إجبار التغليف من اليمين لليسار
RTL_POP = '\u202c'     # إنهاء التغليف

# مصفوفة تقييم "النخبوية" - الخبر الضعيف لا يمر
BASE_ELITE_SCORE = {
    "leak": 4, "exclusive": 4, "hands-on": 3, "benchmark": 3,
    "specs": 2, "chip": 3, "tool": 3, "ai agent": 4,
    "gpu": 2, "new feature": 2, "prototype": 3
}

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

    # === 2. إدارة الذاكرة وقاعدة البيانات ===
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

    # === 3. فلاتر الأمان والذكاء ===
    def _is_throttled(self, task, minutes):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            return r and datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    def _brain(self, mission, context):
        """محرك الصياغة: يمنع الركاكة ويفرض اللهجة الخليجية والمحاذاة"""
        charter = (
            "أنت مستشار تقني خليجي نخبوي. لغتك (خليجية بيضاء) رصينة.\n"
            "قاعدة ذهبية: ابدأ النص بكلمة عربية قوية فوراً. ممنوع مقدمات مثل (ابتكار، هل تبحث، إليك).\n"
            "الهيكل: دخول مباشر في صلب الخبر -> ليش يهم الفرد حالياً -> 3 نقاط بأسلوب (💎⚡🛡️) -> سؤال نخبة.\n"
            "المصطلحات الإنجليزية (بين أقواس). لا تهلوس نهائياً."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.0,
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            content = res.choices[0].message.content.strip()
            # تغليف المحاذاة لضمان السيادة من اليمين
            return f"{RTL_EMBED}{RTL_MARK}{content}{RTL_POP}"
        except: return ""

    # === 4. محرك النشر الطازج (The Freshness Engine) ===
    def post_elite_scoop(self):
        """لا ينشر إلا الأخبار التي لم تتجاوز 24 ساعة ولم تسبق بصمتها"""
        if self._is_throttled("post", 45): return
        
        all_entries = []
        for src in (self.sources + self.reddit_feeds):
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:10]:
                    # الحارس الأول: فلترة التاريخ (24 ساعة فقط)
                    published = datetime(*e.published_parsed[:6])
                    if datetime.now() - published > timedelta(hours=24):
                        continue
                    all_entries.append(e)
            except: continue

        candidates = []
        for e in all_entries:
            text = (e.title + getattr(e, 'description', '')).lower()
            score = sum(v for k, v in BASE_ELITE_SCORE.items() if re.search(rf"\b{k}\b", text))
            # الحارس الثاني: فلترة القيمة (أخبار قوية فقط)
            if score >= 3: candidates.append(e)

        if not candidates: return
        
        # اختيار الخبر الأقوى
        target = random.choice(candidates)
        # الحارس الثالث: بصمة العنوان (منع التكرار الأبدي)
        h = hashlib.sha256(target.title.lower().strip().encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
            
            content = self._brain("حلل هذا السكوب التقني الطازج بلهجة خليجية نُخبوية مباشرة.", target.title)
            if content:
                try:
                    self.x.create_tweet(text=content)
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info(f"✅ تم نشر الخبر: {target.title[:40]}...")
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
                    
                    reply = self._brain("رد خليجي نخبوي رصين ومختصر جداً.", t.text)
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        c.commit()
        except: pass

if __name__ == "__main__":
    bot = SovereignApexBotV102_Final()
    bot.handle_mentions()
    bot.post_elite_scoop()
