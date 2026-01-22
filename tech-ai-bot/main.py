import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# إعداد التسجيل لضمان الـوُضُـوح في سجلات GitHub
logging.basicConfig(level=logging.INFO, format='%(message)s')
load_dotenv()

def generate_tech_content():
    # اختيار مصدر عشوائي لضمان التجديد
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    
    prompt = (
        f"اكتب تغريدة تقنية احترافية بالعربية الفصحى عن خبر حقيقي من {source}.\n"
        "الهيكل: التقنية، الأهمية، نصيحة للمستخدم.\n"
        "#تقنية"
    )
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.7
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ في التوليد: {e}")
        return None

def publish_tweet():
    content = generate_tech_content()
    if not content: return

    try:
        # الاتصال المباشر بنظام V2 (الأكثر استقراراً حالياً)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # النشر
        response = client.create_tweet(text=content[:280])
        if response:
            logging.info(f"✅ تم النشر بنجاح! ID: {response.data['id']}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
