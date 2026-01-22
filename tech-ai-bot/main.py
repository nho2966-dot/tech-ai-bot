import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# إعدادات التسجيل لإظهار المخرجات في GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()

def generate_tech_content():
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    
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
        logging.info(f"🌐 جاري طلب المحتوى من OpenRouter لمصدر: {source}")
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.7
            }
        )
        content = res.json()['choices'][0]['message']['content'].strip()
        return content
    except Exception as e:
        logging.error(f"❌ خطأ في التوليد: {e}")
        return None

def publish_tweet():
    logging.info("🚀 بدء عملية توليد التغريدة...")
    content = generate_tech_content()
    
    if not content:
        logging.error("❌ فشل توليد المحتوى، توقف العملية.")
        return

    try:
        logging.info("🔑 جاري الاتصال بـ X API...")
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # النشر الفعلي
        response = client.create_tweet(text=content[:280])
        
        if response:
            logging.info(f"✅ تم النشر بنجاح! الرابط: https://x.com/i/status/{response.data['id']}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر على X: {e}")

# التأكد من استدعاء الدالة عند تشغيل الملف
if __name__ == "__main__":
    publish_tweet()
