import os, sqlite3, logging, hashlib, random, re, time
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. إعدادات البيئة والحوكمة
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

EDITORIAL_POLICY = {
    "BREAKING": {"min_score": 4, "max_len": 500, "prefix": "🚨 عاجل تقني"},
    "ANALYSIS": {"min_score": 4, "max_len": 25000, "prefix": "🧠 تحليل معمق"},
    "OPINION":  {"min_score": 5, "max_len": 25000, "prefix": "🗣️ رأي تقني"},
    "CONTEST":  {"min_score": 5, "max_len": 280, "prefix": "🏆 مسابقة الأسبوع"},
    "HARVEST":  {"min_score": 5, "max_len": 25000, "prefix": "🗞️ حصاد الأسبوع"}
}

TRUSTED_SOURCES = ["theverge.com", "techcrunch.com", "wired.com", "openai.com", "mit.edu", "reuters.com"]

class TechSovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.year = 2026

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (rh TEXT PRIMARY KEY, tid TEXT, uid TEXT, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # --- أدوات التحقق ومنع التكرار ---
    def _is_duplicate(self, text):
        h = hashlib.sha256(text.strip().encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            return conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone() is not None, h

    def _is_trusted(self, url):
        parsed = urlparse("https://" + url if not url.startswith("http") else url)
        domain = parsed.netloc.lower()
        return any(domain == d or domain.endswith("." + d) for d in TRUSTED_SOURCES)

    # --- محرك التحرير الخليجي ---
    def _generate_content(self, raw_input, mode):
        prompt = (f"أنت رئيس تحرير خليجي تقني في 2026. النمط: {mode}.\n"
                  "1. استخدم لهجة خليجية بيضاء (سلسة وقوية).\n"
                  "2. ضع مصطلحين إنجليزيين على الأقل بين قوسين.\n"
                  "3. ركز على الثورة الصناعية الرابعة وممارسات الأفراد.\n"
                  "أنهِ النص بـ: [SCORE: X/5]")
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": raw_input}],
                temperature=0.4
            )
            return r.choices[0].message.content.strip()
        except: return None

    # --- النظام الآلي للنشر ---
    def publish(self, raw_data, source_url, mode="ANALYSIS"):
        if not self._is_trusted(source_url): return
        
        enhanced = self._generate_content(raw_data, mode)
        if not enhanced: return

        # فحص الجودة والمصطلحات
        score_match = re.search(r"\[SCORE:\s*(\d)/5\]", enhanced)
        score = int(score_match.group(1)) if score_match else 0
        clean_text = re.sub(r"\[.*?\]", "", enhanced).strip()
        terms = re.findall(r"\([A-Za-z][A-Za-z0-9\- ]{2,}\)", clean_text)

        policy = EDITORIAL_POLICY.get(mode)
        if score < policy["min_score"] or len(terms) < 2:
            logging.info(f"🛑 رفض جودة: {mode} | Score: {score}")
            return

        is_dup, h = self._is_duplicate(clean_text)
        if is_dup: return

        full_post = f"{policy['prefix']} {self.year}\n\n{clean_text[:policy['max_len']]}\n\n🔗 المرجع: {source_url}"
        
        try:
            self.x.create_tweet(text=full_post)
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, mode, datetime.now().isoformat()))
            logging.info(f"✅ تم نشر {mode} بنجاح!")
        except Exception as e: logging.error(f"❌ خطأ: {e}")

    # --- المجدول الزمني الذكي (Scheduler) ---
    def auto_run(self):
        day = datetime.now().strftime("%A") # Monday, Friday, etc.
        logging.info(f"📅 فحص الجدول الزمني ليوم: {day}")

        if day == "Monday":
            self.publish("صمم مسابقة تقنية تفاعلية عن أمان الوكلاء الذكيين.", "mit.edu", "CONTEST")
        elif day == "Wednesday":
            self.publish("اطرح استطلاع رأي (Poll) حول تقبّل المجتمع لاستبدال المهام الروتينية بـ AI Agents.", "wired.com", "OPINION")
        elif day == "Friday":
            self.publish("اكتب حصاد الأسبوع لأهم 3 ابتكارات في الحوسبة السيادية.", "techcrunch.com", "HARVEST")
        else:
            self.publish("قدم نصيحة يومية سريعة لتعزيز الإنتاجية باستخدام أدوات الثورة الرابعة.", "openai.com", "BREAKING")

if __name__ == "__main__":
    engine = TechSovereignEngine()
    # تشغيل المحرك (يمكن وضعه في Cron Job ليعمل تلقائياً)
    engine.auto_run()
