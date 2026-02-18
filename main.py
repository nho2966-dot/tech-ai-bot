import os
import time
import random
import logging
import sqlite3
from datetime import datetime

# استيراد المكتبات (تأكد من وجودها في requirements.txt)
import tweepy
from google import genai
from openai import OpenAI
from twilio.rest import Client

class NasserApexBot:
    def __init__(self):
        # إعداد العملاء (Clients) باستخدام مفاتيحك من الصورة
        self.gemini_key = os.getenv("GEMINI_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.xai_key = os.getenv("XAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        # ربط X (تويتر)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def _generate_content_logic(self, prompt):
        """منطق التبديل الآلي بين العقول الستة"""
        # قائمة المحاولات بناءً على Keys المتوفرة عندك
        methods = [
            ("Gemini", self._call_gemini),
            ("OpenAI", self._call_openai),
            ("XAI (Grok)", self._call_xai),
            ("Groq", self._call_groq)
        ]
        
        for name, func in methods:
            try:
                print(f"🤖 محاولة استخدام عقل: {name}...")
                content = func(prompt)
                if content: return content
            except Exception as e:
                print(f"⚠️ {name} مضغوط.. ننتقل للعقل التالي.")
                continue
        return None

    # --- دوال استدعاء العقول ---
    def _call_gemini(self, p):
        client = genai.Client(api_key=self.gemini_key)
        return client.models.generate_content(model="gemini-2.0-flash", contents=p).text

    def _call_openai(self, p):
        client = OpenAI(api_key=self.openai_key)
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}])
        return res.choices[0].message.content

    def _call_xai(self, p):
        client = OpenAI(api_key=self.xai_key, base_url="https://api.x.ai/v1")
        res = client.chat.completions.create(model="grok-beta", messages=[{"role": "user", "content": p}])
        return res.choices[0].message.content

    # --- منطق الواتساب ---
    def notify_nasser(self, msg):
        try:
            client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
            client.messages.create(
                from_='whatsapp:+14155238886',
                body=f"📢 *تنبيه بوت ناصر:*\n{msg}",
                to=f"whatsapp:{os.getenv('MY_PHONE_NUMBER')}"
            )
        except: print("📱 فشل إرسال الواتساب")

# --- التشغيل النهائي المتسلسل ---
if __name__ == "__main__":
    bot = NasserApexBot()
    
    # 1. فحص الردود
    bot.handle_mentions() # أضف منطق المنشن هنا
    
    # 2. الفاصل الزمني العشوائي (بين 5-10 دقائق) كما طلبت
    wait_time = random.randint(300, 600)
    print(f"⏳ انتظار {wait_time//60} دقيقة قبل النشر...")
    time.sleep(wait_time)
    
    # 3. النشر باستخدام العقول الستة
    prompt = "اكتب تغريدة عن أحدث أدوات الذكاء الاصطناعي المفيدة للأفراد بلهجة خليجية."
    final_text = bot._generate_content_logic(prompt)
    
    if final_text:
        bot.x_client.create_tweet(text=final_text[:280])
        bot.notify_nasser("✅ تم النشر بنجاح باستخدام العقول البديلة!")
    else:
        bot.notify_nasser("❌ فشل النشر.. جميع العقول الستة تعتذر عن الخدمة!")
