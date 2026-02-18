import sys
import os
import sqlite3
import random
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

# --- 1. محرك البحث الديناميكي عن المسارات (منع فشل الـ Build) ---
def resolve_paths():
    base = Path(__file__).resolve().parent
    sys.path.extend([str(base), str(base / "src"), str(base / "src" / "core")])
    # التأكد من وجود المجلدات الضرورية
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

resolve_paths()

# --- 2. الاستيراد الآمن للمكتبات ---
try:
    import tweepy
    from google import genai
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display
    # استيراد أدواتك الخاصة من src
    from src.core.ai_writer import AIWriter
    from src.utils.logger import setup_logger
except ImportError as e:
    print(f"❌ نقص في المكتبات أو المسارات: {e}")
    # تأكد من تحديث requirements.txt بـ Pillow و arabic-reshaper و python-bidi

# --- 3. الكائن البرمجي الرئيسي ---

class NasserApexBot:
    def __init__(self):
        self.db_path = "sovereign_apex_v311.db"
        self.font_path = "font.ttf"
        self.logger = setup_logger() if 'setup_logger' in globals() else logging.getLogger(__name__)
        self._init_clients()

    def _init_clients(self):
        """إعداد الاتصال بـ X و Gemini"""
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        # توثيق v1.1 لرفع الصور
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        self.api_v1 = tweepy.API(auth)
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    # --- 4. محرك الردود البصرية المنضبطة (بدون هلوسة) ---

    def create_safe_infographic(self, text_content, output_name="reply_v.png"):
        """رسم نص عربي سليم فوق خلفية تقنية"""
        try:
            # معالجة النص العربي لمنع الحروف المقطعة
            reshaped_text = arabic_reshaper.reshape(text_content)
            display_text = get_display(reshaped_text)

            # إنشاء صورة خلفية (أو فتح قالب من templates)
            img = Image.new('RGB', (1080, 1080), color=(10, 10, 25))
            draw = ImageDraw.Draw(img)
            
            # تحميل الخط المرفق في مشروعك
            if os.path.exists(self.font_path):
                font = ImageFont.truetype(self.font_path, 50)
            else:
                font = ImageFont.load_default()

            # رسم النص في المنتصف (بدون هلوسة بصرية)
            draw.text((100, 500), display_text, font=font, fill=(255, 255, 255))
            
            path = f"data/{output_name}"
            img.save(path)
            return path
        except Exception as e:
            self.logger.error(f"❌ فشل إنتاج الإنفوجرافيك: {e}")
            return None

    # --- 5. منطق الردود والنشر الديناميكي ---

    def handle_mentions(self):
        """الرد الذكي على المتابعين"""
        self.logger.info("🔍 فحص المنشن...")
        mentions = self.x_client.get_users_mentions(id=os.getenv("X_USER_ID"), max_results=5)
        
        if not mentions.data: return

        for tweet in mentions.data:
            if self._is_processed(tweet.id): continue
            
            # توليد رد نصي بلهجة ناصر الخليجية
            prompt = f"رد على هذا الاستفسار التقني بلهجة خليجية بيضاء ومختصرة: {tweet.text}"
            res = self.gemini.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            reply_text = res.text

            # إذا كان السؤال يحتاج توضيح بصري
            if len(tweet.text) > 20: # معيار بسيط للحاجة لشرح بصري
                img_path = self.create_safe_infographic(reply_text[:50]) # ملخص بصري
                media = self.api_v1.media_upload(img_path)
                self.x_client.create_tweet(text=reply_text[:280], media_ids=[media.media_id], in_reply_to_tweet_id=tweet.id)
            else:
                self.x_client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
            
            self._save_history(tweet.id, "REPLY")

    def post_daily_content(self):
        """نشر محتوى ديناميكي (أخبار، مقارنة، استطلاع)"""
        if not self._check_spam_safety(): return

        types = ["أخبار عاجلة", "مقارنة عمالقة", "استطلاع رأي"]
        selected = random.choice(types)
        
        prompt = f"اكتب تغريدة احترافية للأفراد عن '{selected}' في عالم الذكاء الاصطناعي 2026. اللهجة: ناصر الخليجي."
        content = self.gemini.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
        
        res = self.x_client.create_tweet(text=content[:280])
        self._save_history(res.data['id'], selected)

    # --- 6. صمامات الأمان والذاكرة ---

    def _check_spam_safety(self):
        """منع الإغراق: تغريدة كل 3 ساعات، بحد أقصى 4 يومياً"""
        with sqlite3.connect(self.db_path) as conn:
            last = conn.execute("SELECT ts FROM history ORDER BY ts DESC LIMIT 1").fetchone()
            if last and (datetime.now() - datetime.strptime(last[0], '%Y-%m-%d %H:%M:%S') < timedelta(hours=3)):
                return False
            count = conn.execute("SELECT COUNT(*) FROM history WHERE ts > datetime('now', '-1 day')").fetchone()[0]
            return count < 4
        return True

    def _is_processed(self, tid):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM history WHERE hash=?", (str(tid),)).fetchone() is not None

    def _save_history(self, tid, c_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO history (hash, content_type, ts) VALUES (?, ?, datetime('now'))", (str(tid), c_type))

if __name__ == "__main__":
    bot = NasserApexBot()
    # تشغيل المهام
    bot.handle_mentions()
    bot.post_daily_content()
