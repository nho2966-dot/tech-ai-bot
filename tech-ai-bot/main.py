import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(level=logging.INFO)

def generate_tech_content():
    # قائمة المصادر الموثوقة (دون حصر)
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review", "Ars Technica"]
    source = random.choice(sources)
    
    # البرومبت المحسن لإضافة الوسم والمصدر بشكل احترافي
    prompt = (
        f"اكتب تغريدة تقنية احترافية بالعربية الفصحى عن خبر حقيقي من {source}.\n"
        "الهيكل المطلوب:\n"
        "🛡️ التقنية: (اسم الابتكار)\n"
        "💡 الأهمية: (الفائدة بلغة الأرقام)\n"
        "🛠️ التوظيف: (نصيحة للمستخدم)\n"
        f"🌍 المصدر: {source}\n"
        "#تقنية"
    )
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.3
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"خطأ في التوليد: {e}")
        return None

def publish_tweet():
    logging.info("🚀 محاولة النشر باستخدام نظام X API V2...")
    content = generate_tech_content()
    
    if not content:
        logging.error("❌ لم يتم توليد محتوى.")
        return

    try:
        # استخدام نظام V2 حصراً لتجنب خطأ 403 و 453
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # النشر
        response = client.create_tweet(text=content[:280])
        
        if response:
            logging.info(f"✅ تم النشر بنجاح! الرابط: https://x.com/i/status/{response.data['id']}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
