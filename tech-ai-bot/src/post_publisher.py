import os
import tweepy
import logging
import re
import random
from google import genai
from google.genai import types
from openai import OpenAI # ستحتاج لإضافة openai في requirements.txt

logging.basicConfig(level=logging.INFO)

def clean_text(text):
    if not text: return ""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨]', '', text)
    return " ".join(cleaned.split())

def get_pro_tips():
    """محتوى معرفي عالي الجودة في حال فشل جميع النماذج الذكية."""
    tips = [
        {"ar": "خفايا التقنية: استخدام شاشات LTPO يقلل معدل التحديث لـ 1Hz لتوفير البطارية.", "en": "Tech Secrets: LTPO displays drop refresh rates to 1Hz to save battery life."},
        {"ar": "ميزة احترافية: التصوير بصيغة RAW يمنحك تحكماً كاملاً في تعديل الألوان والظلال.", "en": "Pro Tip: Shooting in RAW gives you full control over color and shadow editing."},
        {"ar": "الذكاء الاصطناعي: نماذج RAG تربط الذكاء الاصطناعي ببياناتك المحدثة لحظياً.", "en": "AI Insight: RAG models connect AI to your real-time updated data."}
    ]
    selected = random.choice(tips)
    return f"💡 {selected['ar']}\n---\n{selected['en']}\n#ProTips #AI #Tech2026"

def generate_with_gemini():
    """المحاولة الأولى: البحث عبر Gemini."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key: return None
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        prompt = "ابحث عن خبر تقني عالمي (آخر 7 أيام) واكتب تغريدة بالعربية والإنجليزية مع الأرقام والمصدر."
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(tools=[google_search_tool])
        )
        return clean_text(response.text.strip()) if response.text else None
    except Exception as e:
        logging.error(f"❌ Gemini Error: {e}")
        return None

def generate_with_qwen_groq():
    """المحاولة الثانية: البحث عبر Qwen (من خلال Groq)."""
    try:
        api_key = os.getenv("QWEN_API_KEY") # المفتاح الذي حصلت عليه يبدأ بـ gsk_
        if not api_key: return None
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        completion = client.chat.completions.create(
            model="qwen-2.5-32b",
            messages=[{'role': 'user', 'content': 'هات خبر تقني عالمي جديد (عربي وإنجليزي) مع الأرقام والمصدر.'}]
        )
        return clean_text(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"❌ Groq/Qwen Error: {e}")
        return None

def publish_tech_tweet():
    try:
        # نظام المفاضلة الذكي
        content = generate_with_gemini()
        if not content:
            content = generate_with_qwen_groq()
        if not content:
            content = get_pro_tips()

        # إعدادات النشر على X
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        client.create_tweet(text=content[:280])
        logging.info("🚀 تم النشر بنجاح باستخدام أفضل مصدر متاح!")
    except Exception as e:
        logging.error(f"❌ Critical Failure: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
