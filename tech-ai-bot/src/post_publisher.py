import os
import tweepy
import google.genai as genai
import logging
import random

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO)

def generate_tech_content():
    """توليد محتوى تقني باستخدام Gemini 2.0 Flash."""
    try:
        gemini_key = os.getenv("GEMINI_KEY")
        if not gemini_key:
            raise ValueError("مفتاح GEMINI_KEY غير موجود في Secrets")
            
        client = genai.Client(api_key=gemini_key)
        prompt = "اكتب تغريدة تقنية قصيرة ومفيدة عن الذكاء الاصطناعي باللغة العربية، مع هاشتاقات مناسبة."
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"❌ فشل توليد المحتوى: {e}")
        # محتوى احتياطي في حال فشل Gemini
        fallbacks = [
            "الذكاء الاصطناعي ليس مجرد أدوات، بل هو نهج جديد لحل المشكلات المعقدة. #ذكاء_اصطناعي #تقنية",
            "مستقبل التقنية يكمن في التناغم بين العقل البشري والذكاء الاصطناعي. 🚀 #Tech #AI"
        ]
        return random.choice(fallbacks)

def publish_tech_tweet():
    """نشر التغريدة باستخدام الوضع السابق الموثوق (OAuth 1.0a)."""
    try:
        # تهيئة تويتر بنظام V1.1 (المفاتيح الأربعة فقط)
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"),
            os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"),
            os.getenv("X_ACCESS_SECRET")
        )
        api = tweepy.API(auth)

        # توليد المحتوى
        content = generate_tech_content()

        # النشر الفعلي بالدالة التي نجحت معك سابقاً
        api.update_status(status=content[:280])
        logging.info("✅ تم النشر بنجاح باستخدام الوضع السابق الموثوق!")

    except Exception as e:
        logging.error(f"❌ فشل النشر في الوضع السابق: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
