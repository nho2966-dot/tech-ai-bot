import os
import tweepy
import logging
import re
import random
from google import genai
from google.genai import types

# إعدادات التسجيل لمراقبة أداء البوت
logging.basicConfig(level=logging.INFO)

def clean_text(text):
    """تنظيف النص مع الحفاظ على لغتين والرموز التقنية والإيموجي."""
    # السماح بالحروف العربية، الإنجليزية، الأرقام، ورموز التقنية المختارة
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨]', '', text)
    return " ".join(cleaned.split())

def generate_global_verified_content():
    """توليد محتوى تقني أكاديمي موثق باللغتين العربية والإنجليزية من مصادر عالمية."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            logging.error("❌ GEMINI_KEY غير موجود في المتغيرات البيئية.")
            return None
            
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        # البرومبت الاحترافي لضمان الجودة الأكاديمية والبيانية
        prompt = """
        أنت محلل تقني رصين. ابحث في المصادر التالية خلال الـ 7 أيام الماضية:
        - جامعات: (MIT, Stanford, ETH Zurich, Carnegie Mellon).
        - مراكز أبحاث: (Gartner, IDC, Bloomberg Technology).
        - شركات: (Apple Newsroom, NVIDIA Blog, OpenAI).
        
        المطلوب:
        1. استخرج خبراً واحداً دقيقاً يتضمن أرقاماً، إحصائيات، أو سبقاً علمياً.
        2. صغ التغريدة باللغتين:
           [العربية: عنوان مشوق + تفاصيل الخبر مع الأرقام + المصدر]
           ---
           [English: Translation of the same content]
        3. الوسوم: #AI #Tech2026 #Innovation #تقنية.
        
        اللغة: فصحى عصرية ملكية للعربية، ولغة تقنية دقيقة للإنجليزية.
        ملاحظة: لا تتجاوز 280 حرفاً في المجموع الكلي.
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
        logging.error(f"❌ خطأ أثناء توليد المحتوى: {e}")
        return None

def publish_tech_tweet():
    """تنفيذ عملية النشر على منصة X."""
    try:
        content = generate_global_verified_content()
