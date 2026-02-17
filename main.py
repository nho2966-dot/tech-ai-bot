import os
import sqlite3
import hashlib
import tweepy
import feedparser
import random
import logging
from datetime import datetime, date, timedelta
from openai import OpenAI

# إعداد السجلات الاحترافية
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignStrategicBot:
    def __init__(self):
        self.keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "gemini": os.getenv("GEMINI_KEY")
        }
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_x()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, category TEXT, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")

    def _setup_x(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def select_category(self):
        """توزيع الفئات لضمان التنوع وعدم الملل"""
        categories = ["BREAKING", "COMPARISON", "TIPS", "AI_INSIGHT", "POLL", "VISUAL"]
        # يمكن إضافة منطق هنا لاختيار الفئة بناءً على وقت النشر (مثلاً: نصائح في الصباح، أخبار في العصر)
        return random.choice(categories)

    def generate_strategic_content(self, category, data):
        """صياغة المحتوى بناءً على الفئة المختارة مع روح 'الخبير الخليجي'"""
        prompts = {
            "BREAKING": "صغ هذا الخبر العاجل بلهجة خليجية قوية. ركز على الأرقام الصادمة والفائدة المباشرة للفرد. انهِ بسؤال تحفيزي.",
            "COMPARISON": "اعمل مقارنة 'دسمة' بالأرقام (جدول نصي) بين هذا المنتج ومنافسه أو الجيل السابق. وضح الفرق في الأداء والسعر. من تختار؟",
            "TIPS": "استخرج نصيحة تقنية/أمنية سريعة وعملية للأفراد من هذا المحتوى. خطوات 1-2-3 واضحة جداً. استخدم إيموجي درع حماية.",
            "AI_INSIGHT": "حلل هذه الأداة الذكية الجديدة. اذكر رابطها وكيف توفر وقت المستخدم الخليجي. هل ستغير قواعد اللعبة؟",
            "POLL": "صغ سؤال استطلاع رأي (Poll) ذكي بناءً على هذا التوجه التقني. اذكر خيارين للمقارنة بلهجة خليجية.",
            "VISUAL": "صغ وصفاً بيانياً (Infographic style) يشرح هذا التطور التقني بالأرقام والرموز. اجعل الكلام 'بصرياً' ومرتباً."
        }
        
        system_msg = f"أنت مستشار تقني خليجي متمكن. أسلوبك: {prompts.get(category)}. الحساب مدفوع، المعنى يجب أن يكون مكتملاً وقوياً."
        
        # محاولة تنفيذ (مع نظام الطاف)
        try:
            client = OpenAI(api_key=self.keys["openai"])
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": data}]
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logging.warning(f"⚠️ تعثر عقل OpenAI.. جاري تجربة عقل بديل للفئة {category}")
            return None # سينتقل النظام للعقل التالي في الدورة القادمة

    def run_strategy(self):
        # التأكد من سقف الـ 3 تغريدات
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            if res and res[0] >= 3:
                logging.info("🛡️ تم استهلاك الحد اليومي المخطط له.")
                return

        # جلب البيانات من المصادر الموثوقة (GitHub, RSS, News APIs)
        feed = feedparser.parse("https://www.theverge.com/tech/rss/index.xml")
        category = self.select_category() # اختيار فئة عشوائية لضمان التنوع
        
        for entry in feed.entries[:10]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    content = self.generate_strategic_content(category, f"{entry.title} - {entry.summary}")
                    
                    if content:
                        try:
                            # في حال كانت الفئة POLL، يمكن إضافة منطق خاص بـ poll_options
                            self.x_client.create_tweet(text=content)
                            
                            conn.execute("INSERT INTO history VALUES (?, ?, ?)", (h, category, datetime.now()))
                            conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
                            conn.commit()
                            logging.info(f"🚀 تم نشر محتوى من فئة: {category}")
                            break # نشر واحد في كل دورة (إجمالي 3 يومياً)
                        except Exception as e:
                            logging.error(f"❌ فشل النشر على X: {e}")

if __name__ == "__main__":
    SovereignStrategicBot().run_strategy()
