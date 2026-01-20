import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# 1. إعدادات النظام الأساسية
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def publish_tweet():
    logging.info("🚀 استعادة مهمة النشر المستقرة...")
    
    # قائمة المصادر الموثوقة (دون حصر)
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review", "Ars Technica"]
    source = random.choice(sources)
    
    # البرومبت الملتزم بكافة الاشتراطات (LTPO + الوسم + المصدر)
    prompt = (
        f"اكتب تغريدة تقنية احترافية بالعربية الفصحى عن خبر حقيقي من {source}.\n"
        "الهيكل:\n"
        "🛡️ التقنية: (اسم الابتكار)\n"
        "💡 الأهمية: (الفائدة بلغة الأرقام)\n"
        "🛠️ التوظيف: (نصيحة للمستخدم)\n"
        f"🌍 المصدر: {source}\n"
        "#تقنية"
    )
    
    # التوليد عبر كوين (Llama 3.1 70B)
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.3
            }, timeout=25
        )
        content = res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ فشل التوليد: {e}")
        return

    # 2. عملية النشر بنظام V2 (الطريقة الوحيدة التي نجحت يقيناً)
    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # النشر المباشر
        response = client.create_tweet(text=content[:280])
        if response:
            logging.info(f"✅ تم النشر بنجاح! معرف التغريدة: {response.data['id']}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
