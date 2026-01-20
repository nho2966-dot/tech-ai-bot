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
    # المصادر الشاملة
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    
    prompt = f"اكتب تغريدة تقنية احترافية بالعربية الفصحى عن خبر حقيقي من {source}. الهيكل: 🛡️ التقنية، 💡 الأهمية، 🛠️ التوظيف، 🌍 المصدر: [{source}]. لا تتجاوز 260 حرفاً."
    
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
    except:
        return None

def publish_tweet():
    logging.info("🚀 محاولة النشر باستخدام نظام X API V2 (Free Tier)...")
    content = generate_tech_content()
    
    if not content:
        return

    try:
        # الحل القاطع لمشكلة 453: استخدام Client (V2) مع تمرير كافة المفاتيح
        # هذا هو النظام الوحيد المسموح به للحسابات المجانية الآن
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # استخدام create_tweet حصراً (V2 endpoint)
        response = client.create_tweet(text=content[:280])
        
        if response:
            logging.info(f"✅ تم النشر بنجاح! معرف التغريدة: {response.data['id']}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر النهائي: {e}")

if __name__ == "__main__":
    publish_tweet()
