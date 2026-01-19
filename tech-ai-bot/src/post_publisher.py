import os
import tweepy
import logging
import re
import random
from google import genai
from google.genai import types
from openai import OpenAI

# إعدادات التسجيل لمراقبة أداء الأنظمة الثلاثة
logging.basicConfig(level=logging.INFO)

def clean_text(text):
    """تنظيف النص لضمان توافقه مع معايير النشر العالمية."""
    if not text: return ""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨]', '', text)
    return " ".join(cleaned.split())

def get_pro_tips():
    """المستوى الثالث: مخزن المعلومات الاحترافية (يعمل بدون إنترنت/API)."""
    tips = [
        {"ar": "خفايا التقنية: شاشات LTPO توفر طاقة هائلة بتقليل التحديث لـ 1Hz.", "en": "Tech Secrets: LTPO displays save massive power by dropping refresh to 1Hz."},
        {"ar": "ميزة احترافية: التصوير بصيغة RAW يمنحك مرونة سينمائية في تعديل الألوان.", "en": "Pro Tip: RAW photography offers cinematic flexibility in color grading."},
        {"ar": "ذكاء اصطناعي: نماذج RAG تربط مساعدك الذكي ببياناتك الخاصة لحظياً.", "en": "AI Insight: RAG models link your AI assistant to private data in real-time."}
    ]
    selected = random.choice(tips)
    return f"💡 {selected['ar']}\n---\n{selected['en']}\n#ProTips #AI #Tech2026"

def generate_with_gemini():
    """المستوى الأول: محرك البحث الذكي من جوجل."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key: return None
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        
        prompt = "ابحث عن ابتكار تقني عالمي (آخر 7 أيام) واكتب تغريدة بالعربية والإنجليزية مع الأرقام والمصدر."
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool])
        )
        return clean_text(response.text.strip()) if response.text else None
    except Exception as e:
        logging.error(f"⚠️ Gemini Quota/Error: {e}")
        return None

def generate_with_qwen_groq():
    """المستوى الثاني: التبديل التلقائي لنموذج Qwen عبر منصة Groq السريعة."""
    try:
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key: return None
        
        # الاتصال بمنصة Groq التي تدعم نماذج Qwen
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
