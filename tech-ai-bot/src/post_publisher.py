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
    # إزالة الرموز الغريبة مع الحفاظ على الإيموجي واللغتين
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨🔗🎯🛠️🔋📷]', '', text)
    return " ".join(cleaned.split())

def smart_truncate(content, length=280):
    """يقص النص بذكاء عند نهاية جملة أو مسافة للحفاظ على القيمة المعرفية."""
    if len(content) <= length:
        return content
    
    # محاولة القص عند آخر نقطة أو فاصلة قبل الحد الأقصى
    truncated = content[:length-3]
    last_punctuation = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('؟'))
    
    if last_punctuation > length * 0.7: # إذا كانت النقطة قريبة من النهاية
        return content[:last_punctuation + 1]
    
    # إذا لم توجد نقطة، قص عند آخر مسافة
    last_space = truncated.rfind(' ')
    return content[:last_space] + "..."

def get_pro_tips():
    """محتوى بديل عالي القيمة يركز على التطبيق العملي والمصدر."""
    tips = [
        {
            "ar": "🎯 تقنية RAG في الذكاء الاصطناعي\n💡 الأهمية: تمنع 'التأليف' بربط AI بمصادر موثوقة.\n🛠️ توظيفها: اربط ملفاتك بـ LLM للحصول على نتائج دقيقة من بياناتك فقط.\n🔗 المصدر: IBM",
            "en": "🎯 RAG in AI\n💡 Importance: Prevents AI hallucinations by grounding it in data.\n🛠️ Practice: Connect your docs to LLMs for accurate, source-based results.\n🔗 Source: IBM"
        },
        {
            "ar": "🔋 ميزة LTPO في الشاشات\n💡 الأهمية: سر كفاءة البطارية في الهواتف الرائدة.\n🛠️ توظيفها: فعل وضع 'Adaptive'؛ ستخفض الشاشة التحديث لـ 1Hz تلقائياً لتوفير الطاقة.\n🔗 المصدر: Samsung",
            "en": "🔋 LTPO Tech\n💡 Importance: Key to battery life in flagships.\n🛠️ Practice: Enable 'Adaptive' mode; screen auto-drops to 1Hz to save power.\n🔗 Source: Samsung"
        }
    ]
    selected = random.choice(tips)
    return f"{selected['ar']}\n\n{selected['en']}\n\n#TechTips #Innovation"

def generate_with_gemini():
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key: return None
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        
        prompt = ("ابحث عن خبر تقني عالمي جديد. اكتب تغريدة دسمة تشمل: الميزة، أهميتها، كيفية توظيفها، والمصدر. "
                  "باللغتين العربية والإنجليزية. اجعل النص مختصراً ومركزاً جداً ليناسب 280 حرفاً.")
        
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
            messages=[{"role": "user", "content": "هات خبر تقني جديد (عربي وإنجليزي) مركز جداً مع الميزة والفائدة والمصدر."}]
        )
        return clean_text(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"⚠️ Groq Error: {e}")
        return None

def publish_tech_tweet():
    try:
        logging.info("🚀 محاولة جلب محتوى ذو قيمة عالية...")
        content = generate_with_gemini() or generate_with_qwen_groq() or get_pro_tips()

        final_tweet = smart_truncate(content)

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        client.create_tweet(text=final_tweet)
        logging.info(f"✅ تم النشر! الطول النهائي: {len(final_tweet)}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
