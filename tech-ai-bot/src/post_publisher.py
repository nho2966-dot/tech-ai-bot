import os
import requests
import tweepy
import random
from google import genai
import logging
import hashlib
import time
import re

# إعداد نظام التسجيل
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def clean_arabic_text(text):
    """تنظيف النص لضمان الفصاحة ومنع الرموز الغريبة."""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)🐦🤖🚀💡✨🧠🌍]', '', text)
    return " ".join(cleaned.split())

def generate_content_from_gemini():
    """توليد محتوى تقني فصيح عبر Gemini."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            return None, None
        
        client = genai.Client(api_key=api_key)

        topics = [
            "مستقبل الذكاء الاصطناعي في الإدارة السياسية والمدن الذكية.",
            "أحدث قفزة في الروبوتات الطبية ودورها في العمليات المعقدة.",
            "تأثير تقنيات 2026 على خصوصية البيانات والحرية الفردية."
        ]
        
        selected_topic = random.choice(topics)
        
        prompt = f"""
        أنت خبير تقني ومحرر لغوي محترف. اكتب تغريدة جذابة باللغة العربية الفصحى السليمة عن: {selected_topic}.
        المواصفات: جملة افتتاحية قوية، حقيقة تقنية، وسؤال تفاعلي. 
        ممنوع أي أخطاء إملائية أو رموز غريبة.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        
        if response and response.text:
            return clean_arabic_text(response.text.strip()), "Gemini"
        return None, None
    except Exception as e:
        logging.error(f"❌ فشل Gemini: {e}")
        return None, None

def publish_tech_tweet():
    """الدالة المركزية للنشر - تم تصحيح بلوك try/except هنا."""
    logging.info("🚀 جاري البدء في مهمة النشر...")
    try:
        content, source = generate_content_from_gemini()
        
        if not content:
            content = "هل أنتم مستعدون لمستقبل الذكاء الاصطناعي في 2026؟ شاركونا آراءكم! 🚀 #تقنية"

        # إعداد عميل X
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ أثناء النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
