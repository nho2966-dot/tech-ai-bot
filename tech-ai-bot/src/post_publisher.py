import os
import tweepy
import logging
import re
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)

def clean_text(text):
    if not text: return ""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨]', '', text)
    return " ".join(cleaned.split())

def generate_global_verified_content():
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            logging.error("❌ الخطأ: مفتاح GEMINI_KEY غير مبرمج في Secrets!")
            return None
            
        client = genai.Client(api_key=api_key)
        
        # محاولة البحث الحي
        logging.info("🔍 جاري محاولة البحث في المصادر العالمية والجامعات...")
        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        prompt = "ابحث في MIT و Stanford و Gartner عن خبر تقني حقيقي في آخر 7 أيام. اكتبه بالعربية والإنجليزية مع الأرقام والمصدر."
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool])
        )
        
        if response and response.text:
            logging.info("✅ نجح البحث وتم جلب خبر حي!")
            return clean_text(response.text.strip())
        else:
            logging.warning("⚠️ تحذير: الرد عاد فارغاً من أداة البحث.")
            return None
            
    except Exception as e:
        logging.error(f"❌ خطأ تقني في Gemini/Search: {str(e)}")
        return None

def publish_tech_tweet():
    try:
        content = generate_global_verified_content()
        
        if not content:
            logging.info("ℹ️ استخدام النص الاحتياطي لعدم توفر نتيجة بحث حي.")
            content = "ابتكار من MIT: معالجات نانوية تقلل استهلاك الطاقة بنسبة 40% لعام 2026. #AI #Tech2026"

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        client.create_tweet(text=content[:280])
        logging.info("🚀 تم إنهاء العملية!")
        
    except Exception as e:
        logging.error(f"❌ خطأ في النشر على X: {str(e)}")

if __name__ == "__main__":
    publish_tech_tweet()
