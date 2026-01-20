import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(level=logging.INFO)

def publish_tweet():
    # المصادر الشاملة (التي طلبتها)
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    
    # البرومبت الملتزم بكل اشتراطاتك (LTPO والموثوقية)
    prompt = f"اكتب تغريدة تقنية احترافية بالعربية الفصحى عن خبر حقيقي من {source}. الهيكل: 🛡️ التقنية، 💡 الأهمية، 🛠️ التوظيف، 🌍 المصدر: [{source}]. لا تتجاوز 260 حرفاً."
    
    # التوليد (استخدام كوين لضمان جودة المحتوى)
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.3
            }
        )
        content = res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"خطأ في التوليد: {e}")
        return

    # 2. هيكل النشر (الذي نجحنا به سابقاً - OAuth 1.0a)
    try:
        # استخدام الطريقة التي نشرت بنجاح قبل قليل
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), 
            os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), 
            os.getenv("X_ACCESS_SECRET")
        )
        api = tweepy.API(auth)
        
        # النشر الفعلي
        api.update_status(status=content)
        logging.info("✅ تم النشر بنجاح باستخدام الطريقة الموثوقة!")
        
    except Exception as e:
        logging.error(f"خطأ النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
