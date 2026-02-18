import os
import sys
import time
import random
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# --- 1. إعداد المسارات والبيئة ---
def setup_environment():
    base = Path(__file__).resolve().parent
    sys.path.extend([str(base), str(base / "src")])
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

setup_environment()

# --- 2. الاستيراد المحصن (Safe Imports) ---
try:
    import tweepy
    from google import genai
    from openai import OpenAI
    import arabic_reshaper
    from bidi.algorithm import get_display
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    print(f"⚠️ نقص في المكتبات الأساسية: {e}")

try:
    from twilio.rest import Client
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False
    print("⚠️ مكتبة Twilio غير موجودة، سيعمل البوت بدون تنبيهات واتساب.")

# --- 3. كلاس البوت الرئيسي (عقل ناصر) ---

class NasserApexBot:
    def __init__(self):
        self.db_path = "data/nasser_bot_v3.db"
        self._init_db()
        # جلب المفاتيح من GitHub Secrets
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "xai": os.getenv("XAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY")
        }
        self._init_x_client()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, type TEXT, ts DATETIME)")

    def _init_x_client(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            print("✅ تم الاتصال بمنصة X بنجاح.")
        except Exception as e:
            print(f"❌ فشل الاتصال بمنصة X: {e}")

    # --- 4. محرك العقول الستة (The Failover Engine) ---

    def generate_smart_content(self, prompt):
        """محرك التبديل الآلي بين العقول الستة لضمان الاستمرارية"""
        methods = [
            ("Gemini 2.0", self._call_gemini),
            ("GPT-4o", self._call_openai),
            ("Grok (xAI)", self._call_xai),
            ("Groq Llama", self._call_groq)
        ]

        for name, func in methods:
            try:
                print(f"🤖 محاولة التوليد باستخدام {name}...")
                content = func(prompt)
                if content:
                    print(f"✨ نجح التوليد عبر {name}")
                    return content
            except Exception as e:
                print(f"⚠️ {name} تعثر.. جاري تجربة العقل البديل.")
                time.sleep(2)
        return None

    def _call_gemini(self, p):
        c = genai.Client(api_key=self.keys["gemini"])
        return c.models.generate_content(model="gemini-2.0-flash", contents=p).text

    def _call_openai(self, p):
        c = OpenAI(api_key=self.keys["openai"])
        res = c.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}])
        return res.choices[0].message.content

    def _call_xai(self, p):
        c = OpenAI(api_key=self.keys["xai"], base_url="https://api.x.ai/v1")
        res = c.chat.completions.create(model="grok-beta", messages=[{"role": "user", "content": p}])
        return res.choices[0].message.content

    def _call_groq(self, p):
        c = OpenAI(api_key=self.keys["groq"], base_url="https://api.groq.com/openai/v1")
        res = c.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": p}])
        return res.choices[0].message.content

    # --- 5. نظام التنبيهات والواتساب ---

    def notify(self, message):
        print(f"📢 إشعار: {message}")
        if HAS_TWILIO and os.getenv("TWILIO_SID"):
            try:
                client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
                client.messages.create(
                    from_='whatsapp:+14155238886',
                    body=f"🤖 *بوت ناصر أيبكس:*\n{message}",
                    to=f"whatsapp:{os.getenv('MY_PHONE_NUMBER')}"
                )
            except Exception as e:
                print(f"📱 فشل إرسال واتساب: {e}")

    # --- 6. العمليات التشغيلية ---

    def run_cycle(self):
        # المرحلة 1: فحص المنشن (اختياري)
        print("🔍 جاري فحص المنشن...")
        # (يمكنك إضافة منطق الرد هنا)

        # المرحلة 2: الفاصل الزمني العشوائي (بين 5 إلى 10 دقائق)
        wait = random.randint(300, 600)
        print(f"⏳ سكون بشري لمدة {wait//60} دقيقة...")
        time.sleep(wait)

        # المرحلة 3: توليد ونشر محتوى الذكاء الاصطناعي وأدواته الحديثة
        prompt = "اكتب تغريدة إبداعية عن أداة ذكاء اصطناعي جديدة تفيد الأفراد، بلهجة خليجية بيضاء، مع هاشتاقات تقنية."
        content = self.generate_smart_content(prompt)

        if content:
            try:
                self.x_client.create_tweet(text=content[:280])
                self.notify("✅ تم نشر التغريدة بنجاح باستخدام العقول البديلة.")
            except Exception as e:
                self.notify(f"❌ فشل النشر على X: {e}")
        else:
            self.notify("🚨 انهيار العقول الستة! لم يتمكن أي موديل من التوليد.")

# --- التشغيل الفعلي ---
if __name__ == "__main__":
    bot = NasserApexBot()
    bot.run_cycle()
