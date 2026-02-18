import sys
import os
import sqlite3
import random
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

# --- 1. رادار المسارات الديناميكي (منع فشل الـ Build) ---
def resolve_paths():
    base = Path(__file__).resolve().parent
    # إضافة المجلد الرئيسي ومجلد src لمسار بايثون
    sys.path.extend([str(base), str(base / "src"), str(base / "src" / "core")])
    # إنشاء مجلدات البيانات واللوقز إذا كانت غير موجودة
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

resolve_paths()

# --- 2. الاستيراد الآمن (Safe Import) ---
try:
    import tweepy
    from google import genai
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display
    # محاولة استيراد أدواتك من مجلد src
    from src.core.ai_writer import AIWriter
    from src.utils.logger import setup_logger
except ImportError as e:
    print(f"⚠️ تنبيه: تم تجاوز بعض الاستيرادات، تأكد من ملف requirements.txt: {e}")

# --- 3. محرك ناصر للذكاء الاصطناعي ---

class NasserApexBot:
    def __init__(self):
        self.db_path = "sovereign_apex_v311.db"
        self.font_path = "font.ttf"
        self.logger = logging.getLogger("NasserBot")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        """تجهيز قاعدة البيانات لمنع التكرار والهلوسة"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history 
                (hash TEXT PRIMARY KEY, content_type TEXT, ts DATETIME)
            """)

    def _init_clients(self):
        """الربط مع منصة X و Gemini"""
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        self.api_v1 = tweepy.API(auth)
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    # --- 4. المحرك البصري العربي (صفر أخطاء لغوية) ---

    def generate_visual_content(self, text, output_name="out.png"):
        """إنتاج إنفوجرافيك عربي سليم"""
        try:
            # تصحيح النص العربي (Reshaping & Bidi)
            reshaped = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped)

            # إنشاء خلفية تقنية (Deep Navy Blue)
            img = Image.new('RGB', (1200, 675), color=(5, 15, 35))
            draw = ImageDraw.Draw(img)

            # تحميل الخط العربي المرفق
            font_size = 45
            if os.path.exists(self.font_path):
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.load_default()

            # رسم النص في المنتصف بدقة
            draw.text((100, 300), bidi_text, font=font, fill=(0, 255, 180)) # لون فسفوري تقني
            
            path = f"data/{output_name}"
            img.save(path)
            return path
        except Exception as e:
            print(f"❌ خطأ بصري: {e}")
            return None

    # --- 5. المنطق العملياتي (الردود + النشر) ---

    def handle_mentions(self):
        """الرد الذكي مع مراعاة الـ Rate Limit"""
        print("🔍 جاري فحص المنشن يا ناصر...")
        try:
            mentions = self.x_client.get_users_mentions(id=os.getenv("X_USER_ID"), max_results=5)
            if not mentions.data: return

            for tweet in mentions.data:
                if self._already_processed(tweet.id): continue
                
                # توليد رد خليجي تقني
                prompt = f"رد على الاستفسار بلهجة خليجية بيضاء حول أدوات الذكاء الاصطناعي: {tweet.text}"
                response = self.gemini.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                
                # الرد على X
                self.x_client.create_tweet(text=f"@{tweet.id} {response.text[:250]}", in_reply_to_tweet_id=tweet.id)
                self._save_to_history(tweet.id, "REPLY")
                print(f"✅ تم الرد على: {tweet.id}")
                time.sleep(10) # فاصل بسيط بين الردود

        except tweepy.errors.TooManyRequests:
            print("⚠️ تجاوزت الحد المسموح (429).. بنهدي اللعب شوي.")

    def post_daily_insight(self):
        """نشر محتوى جديد للأفراد"""
        print("📝 جاري تجهيز تغريدة اليوم...")
        try:
            prompt = "اكتب تغريدة عن أحدث أداة ذكاء اصطناعي تفيد الأفراد، بلهجة خليجية قوية ومختصرة."
            res = self.gemini.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            tweet_text = res.text[:280]

            # توليد صورة داعمة للمحتوى
            img_path = self.generate_visual_content(tweet_text[:60]) 
            
            if img_path:
                media = self.api_v1.media_upload(img_path)
                self.x_client.create_tweet(text=tweet_text, media_ids=[media.media_id])
            else:
                self.x_client.create_tweet(text=tweet_text)
            
            print("🚀 تم النشر بنجاح!")
        except Exception as e:
            print(f"❌ فشل النشر: {e}")

    # --- 6. صمامات الأمان ---

    def _already_processed(self, tid):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM history WHERE hash=?", (str(tid),)).fetchone() is not None

    def _save_to_history(self, tid, c_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history VALUES (?, ?, ?)", (str(tid), c_type, datetime.now()))

# --- 7. التشغيل المتسلسل بالفواصل الزمنية ---

if __name__ == "__main__":
    bot = NasserApexBot()
    
    # أولاً: الردود (الأولوية للمتابعين)
    bot.handle_mentions()
    
    # فاصل زمني عشوائي (بين 5 إلى 15 دقيقة) لمنع كشف البوت
    delay = random.randint(300, 900)
    print(f"⏳ انتظار {delay//60} دقيقة قبل النشر لضمان السلوك البشري...")
    time.sleep(delay)
    
    # ثانياً: النشر العام
    bot.post_daily_insight()
