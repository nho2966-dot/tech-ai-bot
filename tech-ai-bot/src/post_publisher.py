import os
import tweepy
import random
from google import genai
import logging
import re

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)

def clean_arabic_text(text):
    """تنظيف النص وضمان جودة الحروف العربية."""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)🐦🤖🚀💡✨🧠🌍]', '', text)
    return " ".join(cleaned.split())

def generate_content_from_gemini():
    """توليد محتوى تقني مع المصدر والوسوم (#)."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        client = genai.Client(api_key=api_key)

        prompt = """
        اكتب تغريدة احترافية عن مستقبل التقنية في 2026.
        المتطلبات:
        1. نص فصيح ومشوق.
        2. المصدر: اذكر "المصدر: ذكاء Gemini التقني".
        3. الوسوم (#): أضف وسوم ذات صلة مثل #ذكاء_اصطناعي #تقنية #مستقبل #AI.
        4. الطول: حافظ على اختصار النص ليكون مناسباً لمنصة X.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        
        if response and response.text:
            return clean_arabic_text(response.text.strip())
        return None
    except Exception as e:
        logging.error(f"❌ خطأ في التوليد: {e}")
        return None

def publish_tech_tweet():
    """نشر التغريدة بالهيكل الجديد."""
    try:
        content = generate_content_from_gemini()
        if not content:
            content = "نحن نعيش عصر التحول الرقمي الأكبر. المصدر: رؤية تقنية. #تقنية #AI"

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر بنجاح مع الوسوم والمصدر!")
    except Exception as e:
        logging.error(f"❌ خطأ في النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
