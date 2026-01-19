import os
import tweepy
import logging
import re
import random
from google import genai
from google.genai import types
from openai import OpenAI

# إعدادات التسجيل لمراقبة النظام
logging.basicConfig(level=logging.INFO)

def clean_text(text):
    """تنظيف النص لضمان جودة النشر وتوافق الرموز."""
    if not text: return ""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨]', '', text)
    return " ".join(cleaned.split())

def get_pro_tips():
    """مخزن المحتوى التعليمي: يشرح الميزة، أهميتها، وكيفية توظيفها عملياً."""
    tips = [
        {
            "ar": "🎯 تقنية RAG في الذكاء الاصطناعي\n💡 الأهمية: تمنع 'هلوسة' النماذج عبر ربطها بمصادر موثوقة.\n🛠️ توظيفها: اربط ملفاتك الخاصة بـ LLM عبر أدوات RAG للحصول على إجابات دقيقة من داخل بياناتك فقط.\n🔗 المصدر: IBM Research",
            "en": "🎯 RAG in AI\n💡 Importance: Prevents AI hallucinations by grounding it in trusted data.\n🛠️ Practice: Connect your private docs to LLMs using RAG tools for source-based accurate answers.\n🔗 Source: IBM Research"
        },
        {
            "ar": "🔋 ميزة LTPO في الشاشات\n💡 الأهمية: السر خلف كفاءة البطارية في الهواتف الرائدة.\n🛠️ توظيفها: فعل وضع 'Adaptive'؛ الشاشة ستخفض التحديث لـ 1Hz تلقائياً عند السكون لتوفير الطاقة.\n🔗 المصدر: Samsung Display",
            "en": "🔋 LTPO Display Tech\n💡 Importance: The key to battery efficiency in flagship phones.\n🛠️ Practice: Enable 'Adaptive' mode; the screen will auto-drop to 1Hz when idle to save power.\n🔗 Source: Samsung Display"
        },
        {
            "ar": "📷 التصوير بصيغة RAW/ProRAW\n💡 الأهمية: الاحتفاظ بكامل بيانات الإضاءة والألوان دون معالجة ضارة.\n🛠️ توظيفها: استخدمها في الإضاءة الصعبة، ثم عدل 'Shadows' في Lightroom لنتائج سينمائية.\n🔗 المصدر: Adobe Professional",
            "en": "📷 RAW/ProRAW Photography\n💡 Importance: Preserves all light and color data without destructive processing.\n🛠️ Practice: Use it for tricky lighting, then edit Shadows in Lightroom for cinematic results.\n🔗 Source: Adobe Professional"
        }
    ]
    selected = random.choice(tips)
    return f"{selected['ar']}\n\n{selected['en']}\n\n#AI #TechTips #Innovation #خفايا_التقنية"

def generate_with_gemini():
    """المستوى الأول: البحث العالمي عبر Gemini 2.0."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key: return None
        client = genai.Client(api_key=api_key)
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        
        prompt = "ابحث عن خبر تقني عالمي جديد (آخر 7 أيام). اكتب تغريدة دسمة: الميزة، أهميتها للمستخدم، كيفية توظيفها، والمصدر. باللغتين العربية والإنجليزية مع الهاشتاقات."
        
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
    """المستوى الثاني: البديل السريع عبر Qwen/Groq."""
    try:
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        
        completion = client.chat.completions.create(
            model="qwen-2.5-32b",
            messages=[
                {"role": "system", "content": "أنت خبير تقني تشرح الميزات وأهميتها وتطبيقها العملي بالعربي والإنجليزي مع المصادر."},
                {"role": "user", "content": "هات خبر تقني عالمي جديد (آخر 7 أيام) بصيغة دسمة ومفيدة للمستخدم."}
            ]
        )
        return clean_text(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"⚠️ Groq/Qwen Error: {e}")
        return None

def publish_tech_tweet():
    """المحرك الرئيسي لنظام النشر الذكي."""
    try:
        logging.info("🚀 جاري محاولة استخراج أفضل محتوى تقني...")
        
        content = generate_with_gemini()
        if not content:
            logging.info("🔄 انتقل إلى الخطة البديلة: Qwen/Groq...")
            content = generate_with_qwen_groq()
        if not content:
            logging.info("💡 استخدم الخطة الاحتياطية: دليل المستخدم الذكي...")
            content = get_pro_tips()

        # إعدادات X (Twitter)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        if content:
            client.create_tweet(text=content[:280]) # ضمان عدم تجاوز حد الحروف
            logging.info("✅ تم النشر بنجاح!")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
