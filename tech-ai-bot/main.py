import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def generate_tech_content():
    # مصادر متخصصة في الذكاء الاصطناعي، الأمن، والأجهزة
    sources = ["The Verge", "TechCrunch", "Wired", "MIT Tech Review", "9to5Mac", "BleepingComputer"]
    source = random.choice(sources)
    
    # البرومبت المكثف لضمان الحداثة والفائدة العالية
    prompt = (
        f"اكتب تغريدة تقنية احترافية جداً بالعربية الفصحى بناءً على أحدث تقارير {source}.\n"
        "المواضيع المطلوبة: (اختر واحداً فقط من: مستجدات الذكاء الاصطناعي، أمن المعلومات، الأمن السيبراني، أو أحدث إصدارات الأجهزة الذكية ومميزاتها).\n"
        "الشروط:\n"
        "1. المعلومة يجب أن تكون حديثة جداً ومفيدة عملياً.\n"
        "2. التركيز على نصيحة تقنية في الاستخدام أو النشر الآمن.\n"
        "الهيكل المطلوب:\n"
        "🛡️ التقنية: (اسم الابتكار أو الخبر)\n"
        "💡 الأهمية: (الفائدة أو التأثير بدقة)\n"
        "🛠️ نصيحة الاستخدام: (إرشاد عملي للمستخدم)\n"
        f"🌍 المصدر: {source}\n"
        "#تقنية #ذكاء_اصطناعي #أمن_سيبراني"
    )
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "system", "content": "أنت خبير تقني مطلع على أحدث مستجدات التقنية والأمن السيبراني."},
                             {"role": "user", "content": prompt}], 
                "temperature": 0.4 # درجة حرارة متزنة لضمان الدقة مع الإبداع
            }, timeout=25
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ في التوليد: {e}")
        return None

def publish_tweet():
    logging.info("🚀 جاري توليد محتوى تقني فائق الجودة ونشره...")
    content = generate_tech_content()
    
    if not content: return

    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # النشر مع ضمان عدم تجاوز الطول المسموح
        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر بنجاح وفق المعايير الجديدة!")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
