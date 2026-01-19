import os
import tweepy
from google import genai
from google.genai import types
import logging
import re

logging.basicConfig(level=logging.INFO)

def clean_text(text):
    """تنظيف النص مع الحفاظ على الحروف العربية والإنجليزية والإيموجي."""
    # نسمح بالحروف العربية، الإنجليزية، الأرقام، والرموز التقنية
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈]', '', text)
    return " ".join(cleaned.split())

def generate_global_content():
    """توليد محتوى تقني أكاديمي وبياني باللغتين العربية والإنجليزية."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        prompt = """
        بصفتك محللاً تقنياً عالمياً، ابحث في أحدث أبحاث الجامعات (MIT, Stanford, ETH Zurich) أو تقارير (Gartner, Reuters) لعام 2026.
        الهدف: استخراج خبر دسم يحتوي على أرقام أو بيانات تقنية.
        
        قم بصياغة التغريدة بالترتيب التالي:
        1. النص العربي: (عنوان مشوق + المعلومة التقنية والبيانية بأسلوب فصيح + المصدر).
        2. فاصلاً بسيطاً (مثل خط أو إيموجي).
        3. النص الإنجليزي: (ترجمة احترافية ودقيقة لنفس المحتوى السابق).
        4. وسوم مشتركة: #AI #Tech2026 #MIT #Stanford #تقنية #ذكاء_اصطناعي.
        
        ملاحظة: تأكد من أن إجمالي النص لا يتجاوز 280 حرفاً قدر الإمكان، وإذا كان الخبر طويلاً، ركز على الجوهر في اللغتين.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool])
        )
        
        if response and response.text:
            return clean_text(response.text.strip())
        return None
    except Exception as e:
        logging.error(f"❌ خطأ في التوليد العالمي: {e}")
        return None

def publish_tech_tweet():
    try:
        content = generate_global_content()
        if not content:
            content = "نتابع أحدث ابتكارات 2026 عالمياً. 🌐 Monitoring the latest 2026 innovations globally. #Tech #AI"

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        client.create_tweet(text=content[:280])
        logging.info("✅ تم نشر التغريدة العالمية بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ في النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
