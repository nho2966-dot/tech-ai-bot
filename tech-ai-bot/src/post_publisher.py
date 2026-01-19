import os
import tweepy
from google import genai
from google.genai import types # لاستخدام أدوات البحث
import logging
import re

logging.basicConfig(level=logging.INFO)

def clean_arabic_text(text):
    """تنظيف النص وضمان الفصاحة."""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)🐦🤖🚀💡✨🧠🌍📱💻]', '', text)
    return " ".join(cleaned.split())

def generate_verified_content():
    """توليد محتوى مبني على بحث حقيقي من مصادر موثوقة."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        client = genai.Client(api_key=api_key)

        # تفعيل أداة البحث من جوجل للوصول لأحدث الأخبار الموثقة
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        prompt = """
        ابحث الآن عن أحدث خبر تقني موثق (أو تسريب مؤكد من مصدر موثوق) لعام 2026.
        المصادر المطلوبة: (Apple Newsroom, Samsung News, The Verge, Reuters Technology).
        
        بعد البحث، اكتب تغريدة باللغة العربية تشمل:
        1. الخبر الحقيقي مع ذكر أرقام أو مواصفات دقيقة.
        2. اسم المصدر العالمي الذي نقل الخبر (مثلاً: وفقاً لـ رويترز).
        3. وسم #خبر_موثق ووسوم تقنية ذات صلة.
        
        صيغة التغريدة: يجب أن تكون رصينة، فصيحة، وبعيدة عن المبالغة.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool] # تم تفعيل البحث الحي هنا
            )
        )
        
        if response and response.text:
            return clean_arabic_text(response.text.strip())
        return None
    except Exception as e:
        logging.error(f"❌ خطأ في البحث والتوليد: {e}")
        return None

def publish_tech_tweet():
    try:
        content = generate_verified_content()
        if not content:
            content = "نعتذر، لم نتمكن من التحقق من خبر موثق حالياً. سنوافيكم بجديد التقنية فور تأكيده. #تقنية #AI"

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        client.create_tweet(text=content[:280])
        logging.info("✅ تم نشر خبر موثق بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ في النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
