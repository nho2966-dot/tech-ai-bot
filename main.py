import os, sqlite3, logging, hashlib, random, re
from datetime import datetime, timedelta
import tweepy, feedparser, requests
from openai import OpenAI
from dotenv import load_dotenv

# === 1. الهوية والبروتوكولات السيادية ===
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
DB_FILE = "sovereign_memory.db"

# رموز التحكم في المحاذاة (Unicode RTL Protocols)
RTL_MARK = '\u200f'    
RTL_EMBED = '\u202b'   
RTL_POP = '\u202c'     

# مصفوفة تقييم النخبوية - الأخبار القوية فقط هي من تمر
BASE_ELITE_SCORE = {
    "leak": 5, "exclusive": 5, "ai agent": 5, "benchmark": 4,
    "hands-on": 4, "chip": 4, "gpu": 3, "specs": 3, "linux": 3,
    "breakthrough": 5, "prototype": 4, "quantum": 5, "gpu": 4
}

class SovereignApexBotV105:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://venturebeat.com/feed/",
            "https://wccftech.com/feed/"
        ]

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")
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
            if r:
                return datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)
            return False

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    def _brain(self, mission, context):
        """محرك الأنسنة السيادية: صياغة بشرية انسيابية بعيدة عن النمطية"""
        charter = (
            "أنت مستشار تقني خليجي متمكن. لغتك (خليجية بيضاء) ذكية، حوارية، وغير رسمية بزيادة.\n"
            "⚠️ قواعد الأنسنة الصارمة:\n"
            "1. ممنوع استخدام كلمات العنونة (شرارة، تحليل، نقطة، سؤال).\n"
            "2. ممنوع تبدأ بكلمات (تقنية، ابتكار، إعلان، خبر).\n"
            "3. ادخل في صلب الفائدة بأسلوب 'خبير يسولف مع ربع مطلعين'. استخدم (تخيل، الصراحة، اللي صاير).\n"
            "4. ادمج الرموز (💎⚡🛡️) داخل الكلام لتعزيز المعنى، وليس كقائمة.\n"
            "5. المصطلحات الإنجليزية بين أقواس ( ). المحاذاة RTL.\n"
            "6. اجعل الختام سؤالاً عفوياً يفتح نقاشاً حقيقياً."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.4, # حرارة متوازنة للإبداع اللغوي
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            content = res.choices[0].message.content.strip()
            return f"{RTL_EMBED}{RTL_MARK}{content}{RTL_POP}"
        except: return ""

    def post_elite_scoop(self):
        """محرك النشر: حماية مشددة، فلترة تاريخية، وبصمة فريدة لمنع التكرار"""
        
        # حماية الهوية: فاصل 90 دقيقة + عشوائية بشرية
        wait_interval = 90 + random.randint(0, 15)
        if self._is_throttled("post", wait_interval): return
        
        candidates = []
        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:10]:
                    # فلترة الحداثة (24 ساعة فقط)
                    pub_date = datetime(*e.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(hours=24): continue
                    
                    # تقييم النخبوية
                    score = sum(v for k, v in BASE_ELITE_SCORE.items() if k in e.title.lower())
                    if score >= 4: candidates.append(e)
            except: continue

        if not candidates: return
        
        # اختيار الأحدث والأقوى تقييماً
        candidates.sort(key=lambda x: datetime(*x.published_parsed[:6]), reverse=True)
        target = candidates[0]
        
        # بصمة العنوان (تنظيف شامل لمنع تكرار نفس الخبر من مصادر مختلفة)
        clean_id = re.sub(r'\W+', '', target.title.lower())
        h = hashlib.sha256(clean_id.encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
            
            content = self._brain("صغ هذا السكوب بأسلوب خبير تقني خليجي يسولف مع متابعيه، ركز على الفائدة.", target.title)
            
            if content and len(content) > 50:
                try:
                    self.x.create_tweet(text=content)
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info(f"🎯 تم نشر تغريدة مؤنسنة: {target.title[:30]}")
                except Exception as e:
                    logging.error(f"X API Error: {e}")

if __name__ == "__main__":
    bot = SovereignApexBotV105()
    bot.post_elite_scoop()
