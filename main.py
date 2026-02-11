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

# مصفوفة تقييم النخبوية - رفعنا المعايير لضمان جودة المحتوى (أخبار الأفراد والصناعة 4.0)
BASE_ELITE_SCORE = {
    "leak": 5, "exclusive": 5, "ai agent": 5, "robot": 4,
    "chip": 4, "gpu": 4, "linux": 3, "breakthrough": 5,
    "automation": 4, "optimization": 4, "future": 3
}

class SovereignApexBotV108:
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
        """محرك النخبوية الخليجية: لغة بيضاء، رصينة، ومباشرة تقتل الركاكة"""
        charter = (
            "أنت مستشار تقني خليجي متمكن. لغتك (خليجية بيضاء رصينة) حصراً.\n"
            "⚠️ قواعد صارمة للغة والأسلوب:\n"
            "1. ممنوع منعاً باتاً الكلمات (الشامية، المصرية، أو العامية المبتذلة) مثل: (شو، كتير، يا رفاق، هيك، منيح، أوي).\n"
            "2. استخدم المفردات الخليجية البيضاء الرصينة: (الصراحة، الحقيقة، اللي صاير، تخيل، تفرق معاك، بلمحة بصر).\n"
            "3. ادخل في صلب الموضوع فوراً (بدون مقدمات ترويجية أو كلمات مثل: تقنية، ابتكار، يمثل، يعد).\n"
            "4. ادمج الرموز (💎⚡🛡️) داخل السياق لتعزيز القيمة التقنية للفرد وممارسات الثورة الصناعية الرابعة.\n"
            "5. المصطلحات الإنجليزية بين أقواس ( ) وبإملاء صحيح 100%.\n"
            "6. الختام يكون سؤالاً ذكياً يمس 'إنتاجية' أو 'خصوصية' المتابع الخليجي.\n"
            "7. إجبار النص على البدء من اليمين RTL."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.2, # انضباط لغوي عالي
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            content = res.choices[0].message.content.strip()
            return f"{RTL_EMBED}{RTL_MARK}{content}{RTL_POP}"
        except: return ""

    def post_elite_scoop(self):
        """محرك النشر: حماية 90 دقيقة، فلترة تاريخية، ومنع تكرار بصمي صارم"""
        
        # حماية الهوية السيادية من الـ Spam
        wait_interval = 90 + random.randint(0, 15)
        if self._is_throttled("post", wait_interval): return
        
        candidates = []
        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:15]:
                    # الحارس الأول: فلترة الحداثة (24 ساعة)
                    pub_date = datetime(*e.published_parsed[:6])
                    if datetime.now() - pub_date > timedelta(hours=24): continue
                    
                    # الحارس الثاني: تقييم النخبوية (درجة 4 فأعلى)
                    score = sum(v for k, v in BASE_ELITE_SCORE.items() if k in e.title.lower())
                    if score >= 4: candidates.append(e)
            except: continue

        if not candidates: return
        
        # اختيار الخبر الأحدث
        candidates.sort(key=lambda x: datetime(*x.published_parsed[:6]), reverse=True)
        target = candidates[0]
        
        # الحارس الثالث: منع التكرار البصمي (تنظيف العنوان تماماً)
        clean_id = re.sub(r'[^a-zA-Z0-9]', '', target.title.lower())
        h = hashlib.sha256(clean_id.encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
            
            content = self._brain("صغ زبدة هذا الخبر بلهجة خليجية بيضاء نُخبوية مباشرة جداً.", target.title)
            
            if content and len(content) > 60:
                try:
                    self.x.create_tweet(text=content)
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info(f"✅ تم النشر السيادي: {target.title[:30]}")
                except Exception as e:
                    logging.error(f"X Error: {e}")

if __name__ == "__main__":
    bot = SovereignApexBotV108()
    bot.post_elite_scoop()
