import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy
import feedparser
from openai import OpenAI
from dotenv import load_dotenv

# 1. سياسة الامتثال والحوكمة (Strict Compliance Policy)
# تم استبعاد أي إشارة للثورة الصناعية الرابعة نهائياً
CONTENT_POLICY = (
    "أنت خبير تقني محترف ومراقب امتثال. تلتزم حصرياً بالمجالات التالية: "
    "1. الذكاء الاصطناعي وأدواته العملية. 2. الأجهزة الذكية ومميزاتها. "
    "3. خوارزميات ومنصات التواصل الاجتماعي. 4. الأمن السيبراني وتوعية الأفراد. "
    "5. الأخبار التقنية الحصرية (Scoops). "
    "القواعد الصارمة: "
    "- الهيكل: (Hook جذاب خليجي) -> (تحليل تقني عميق) -> (الأثر العملي للفرد) -> (CTA تحفيزي). "
    "- يمنع الهلوسة أو قص النصوص. "
    "- يمنع ذكر 'الثورة الصناعية الرابعة' تماماً."
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# 2. محرك التفاعل والذكاء التحريري
class SovereignEditorialEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def generate_thread(self, raw_data):
        """بناء ثريد احترافي جداً دون قص أو هلوسة"""
        prompt = (
            f"{CONTENT_POLICY}\n"
            "حوّل النص التالي إلى ثريد نخبوي. تأكد أن كل تغريدة فكرة مكتملة ولا تتعرض للقص. "
            "افصل بين التغريدات بعلامة '---'."
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": raw_data}]
            )
            return [t.strip() for t in r.choices[0].message.content.split("---") if len(t.strip()) > 10]
        except Exception as e:
            logging.error(f"❌ خطأ في توليد المحتوى: {e}")
            return []

# 3. محرك البحث عن الأخبار الحصرية (Scoop Finder)
class TechScoopEngine:
    def __init__(self, ai_client):
        self.ai = ai_client
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss"
        ]

    def get_validated_scoop(self):
        for url in self.sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # فحص أحدث 5 أخبار فقط لضمان الحصرية
                check_prompt = f"{CONTENT_POLICY}\nهل هذا الخبر يمتثل للتخصصات الخمسة؟ أجب بـ 'PASS' أو 'REJECT'.\nالخبر: {entry.title}"
                res = self.ai.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "user", "content": check_prompt}]
                )
                if "PASS" in res.choices[0].message.content:
                    return f"{entry.title}\n{entry.description}"
        return None

# 4. الأوركسترا الرئيسية (التي تحفظ الإنجاز التراكمي)
class SovereignEngineV42:
    def __init__(self):
        self._db_setup()
        self._client_setup()
        self.editor = SovereignEditorialEngine(self.x, self.ai)
        self.scooper = TechScoopEngine(self.ai)

    def _db_setup(self):
        with sqlite3.connect("tech_om_sovereign_v42.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, dt TEXT)")

    def _client_setup(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def execute_mission(self):
        # 1. جلب خبر حصري ممتثل للسياسة
        raw_scoop = self.scooper.get_validated_scoop()
        if not raw_scoop: return

        # 2. منع التكرار
        h = hashlib.sha256(raw_scoop.encode()).hexdigest()
        with sqlite3.connect("tech_om_sovereign_v42.db") as conn:
            if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone(): return

            # 3. بناء الثريد النخبوي
            tweets = self.editor.generate_thread(raw_scoop)
            prev_id = None
            for i, txt in enumerate(tweets):
                # تأخير رصين لمنع الـ 429
                time.sleep(random.randint(120, 240))
                
                # إضافة بصمة زمنية فريدة للتغريدة الأولى (منع 403)
                if i == 0:
                    txt += f"\n.\n🕒 {datetime.now().strftime('%H:%M')}"

                res = self.x.create_tweet(text=txt, in_reply_to_tweet_id=prev_id)
                prev_id = res.data['id']
                logging.info(f"✅ نشر التغريدة {i+1} بنجاح.")

            conn.execute("INSERT INTO vault VALUES (?, ?)", (h, datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEngineV42()
    bot.execute_mission()
