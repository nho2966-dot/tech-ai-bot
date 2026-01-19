import os
import tweepy
import logging
import re
import random
from google import genai
from google.genai import types
from openai import OpenAI

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO)

def clean_text(text):
    if not text: return ""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨]', '', text)
    return " ".join(cleaned.split())

def get_pro_tips():
    tips = [
        {"ar": "خفايا التقنية: شاشات LTPO توفر طاقة هائلة بتقليل التحديث لـ 1Hz.", "en": "Tech Secrets: LTPO displays save massive power by dropping refresh to 1Hz."},
        {"ar": "ميزة احترافية: التصوير بصيغة RAW يمنحك مرونة سينمائية في تعديل الألوان.", "en": "Pro Tip: RAW photography offers cinematic flexibility in color grading."},
        {"ar": "ذكاء اصطناعي: نماذج RAG تربط مساعدك الذكي ببياناتك الخاصة لحظياً.", "en": "AI Insight: RAG models link your AI assistant to private data in real-time."}
    ]
    selected = random.choice(tips)
    return f"💡 {selected['ar']}\n---\n{selected['en']}\n#ProTips #AI #Tech2026"

def generate_with_gemini():
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key: return None
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        prompt = "ابحث عن ابتكار تقني عالمي جديد (آخر 7 أيام) واكتب تغريدة بالعربية والإنجليزية مع الأرقام والمصدر."
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool])
        )
        return clean_text(response.text.strip()) if response.text else None
    except Exception as e:
        logging.error(f"⚠️ Gemini Error: {e}")
        return None

def generate_with_qwen_groq():
    try:
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        completion = client.chat.completions.create(
            model="qwen-2.5-32b",
            messages=[{"role": "user", "content": "هات خبر تقني عالمي جديد (عربي وإنجليزي) مع الأرقام والمصدر."}]
        )
        return clean_text(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"⚠️ Groq/Qwen Error: {e}")
        return None

def publish_tech_tweet():
    try:
        logging.info("🚀 بدء تشغيل المنظومة الموحدة...")
        content = generate_with_gemini()
        
        if not content:
            logging.info("🔄 التبديل إلى Qwen/Groq...")
            content = generate_with_qwen_groq()
            
        if not content:
            logging.info("💡 التبديل إلى المحتوى البديل...")
            content = get_pro_tips()

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        if content:
            client.create_tweet(text=content[:280])
            logging.info("✅ تم النشر بنجاح!")
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
