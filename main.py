import os, sqlite3, logging, hashlib, random, textwrap, re, time
from datetime import datetime
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# إعدادات البيئة والتنبيهات
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

class TechSovereignMaster:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.quality_threshold = 4  # رفعنا سقف الجودة لعيون الـ Premium

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS tech_vault 
                         (h TEXT PRIMARY KEY, type TEXT, score INTEGER, content TEXT, dt TEXT)""")
            conn.commit()

    def _init_clients(self):
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            # استخدام محرك بحث قوي عبر OpenRouter لضمان صفر هلوسة
            self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        except Exception as e:
            logging.error(f"❌ خطأ في تهيئة المفاتيح: {e}")

    def _get_realtime_data(self):
        """جلب سياق حقيقي من إنترنت 2026 لضمان الدقة"""
        try:
            prompt = "ما هي آخر تطورات الثورة الصناعية الرابعة والأدوات التقنية للأفراد اليوم 5 فبراير 2026؟"
            r = self.ai.chat.completions.create(
                model="google/gemini-2.0-flash-exp:free",
                messages=[{"role": "user", "content": prompt}]
            )
            return r.choices[0].message.content.strip()
        except: return "الوكلاء المستقلون (AI Agents) والإنتاجية العميقة."

    def _ai_judge_and_enhance(self, raw_draft, mode):
        """المدقق الآلي: يضمن اللغة الخليجية، الدقة، ويضع الدرجة"""
        judge_prompt = (
            "أنت مدقق محتوى خليجي تقني رفيع المستوى. راجع النص التالي:\n"
            "1. حوّل اللغة إلى لهجة خليجية بيضاء (سلسة وقريبة للشباب).\n"
            "2. تأكد من وجود مصطلحات إنجليزية دقيقة بين قوسين.\n"
            "3. ارفع العمق التقني (Deep Insight)؛ لا تكتفِ بالسطحيات.\n"
            "4. إذا كان المحتوى 'حصاد' اجعله طويلاً ومفصلاً (Premium Style).\n"
            "في النهاية أضف: [SCORE: X/5] (ارفض أي شيء أقل من 4 بكلمة REJECT)."
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": judge_prompt}, {"role": "user", "content": raw_draft}],
                temperature=0.3
            )
            return r.choices[0].message.content.strip()
        except: return None

    def _generate_core_content(self, context, mode):
        """توليد المحتوى بناءً على النمط المطلوب"""
        templates = {
            "DAILY": "اكتب نصيحة تقنية 'حارة' وعملية للشباب بناءً على {context}. ابدأ بـ 'يا شباب..'.",
            "HARVEST": "اكتب حصاد الأسبوع التقني بشكل مفصل جداً. ركز على الفرص الوظيفية والمالية في 2026.",
            "CONTEST": "صمم مسابقة تقنية أسبوعية (تحدي ذكاء) بلهجة خليجية. السؤال عن {context}."
        }
        
        system_p = "أنت خبير تقني خليجي في 2026. تخصصك الثورة الصناعية الرابعة وتمكين الأفراد. لا تهلوس أبدأ."
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_p}, {"role": "user", "content": templates[mode].format(context=context)}],
                temperature=0.7
            )
            return r.choices[0].message.content.strip()
        except: return None

    def run_engine(self, mode="DAILY"):
        logging.info(f"🚀 بدء محرك النشر بنمط: {mode}")
        
        # 1. جلب سياق حي
        context = self._get_realtime_data()
        
        # 2. توليد المسودة
        raw_draft = self._generate_core_content(context, mode)
        if not raw_draft: return

        # 3. التدقيق والتحسين (الطبقة السيادية)
        final_post = self._ai_judge_and_enhance(raw_draft, mode)
        
        if not final_post or "REJECT" in final_post.upper():
            logging.warning("⚠️ تم رفض المحتوى لعدم استيفاء معايير الجودة.")
            return

        # 4. تنظيف النص وفحص المعايير البرمجية
        score_match = re.search(r"\[SCORE: (\d)/5\]", final_post)
        score = int(score_match.group(1)) if score_match else 0
        clean_text = re.sub(r"\[.*?\]", "", final_post).strip()

        if score < self.quality_threshold or not re.search(r"\([A-Za-z ]+\)", clean_text):
            logging.warning("❌ فشل في اختبارات الجودة البرمجية (المصطلحات أو الدرجة).")
            return

        # 5. فحص التكرار والنشر
        h = hashlib.sha256(clean_text.encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM tech_vault WHERE h=?", (h,)).fetchone():
                logging.info("♻️ محتوى مكرر، تم الإيقاف.")
                return

            try:
                # بفضل اشتراك Premium، ننشر النص كاملاً مهما كان طوله
                self.x.create_tweet(text=clean_text)
                conn.execute("INSERT INTO tech_vault VALUES (?, ?, ?, ?, ?)", 
                             (h, mode, score, clean_text, datetime.now().isoformat()))
                logging.info(f"✅ تم النشر بنجاح! السكور: {score}/5")
            except Exception as e:
                logging.error(f"❌ فشل النشر على X: {e}")

if __name__ == "__main__":
    engine = TechSovereignMaster()
    
    # مثال لتشغيل الحصاد والمسابقة (يُفضل جدولتها أسبوعياً)
    # engine.run_engine(mode="HARVEST")
    # engine.run_engine(mode="CONTEST")
    
    # التشغيل اليومي الاعتيادي
    engine.run_engine(mode="DAILY")
