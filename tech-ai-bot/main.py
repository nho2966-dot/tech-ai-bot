import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# إعداد التسجيل لضمان الـوُضُـوح الاحترافي
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

def generate_premium_analysis():
    sources = ["MIT Tech Review", "Bloomberg Technology", "Wired", "The Verge"]
    source = random.choice(sources)
    
    # برومبت مصمم لإنتاج محتوى طويل وعميق (Premium Style)
    prompt = (
        f"بناءً على تقارير {source} الأخيرة، اكتب مقالاً تقنياً قصيراً ومكثفاً بالعربية الفصحى (حوالي 800 حرف).\n"
        "الهيكل المطلوب:\n"
        "🔹 العنوان: (عنوان مثير وجذاب)\n\n"
        "📍 المشهد التقني: (شرح عميق للابتكار الحالي)\n\n"
        "📈 التأثير الاستراتيجي: (كيف سيغير هذا العالم أو السوق بلغة الأرقام)\n\n"
        "💡 وجهة نظر: (نصيحة تحليلية للمهتمين بالمستقبل التقني)\n\n"
        "استخدم لغة قوية وفصيحة.\n"
        f"🌍 المصدر المرجعي: {source}\n"
        "#تقنية #تحليل_استراتيجي #X_Premium"
    )
    
    try:
        logging.info(f"🌐 جاري طلب تحليل معمق لمصدر: {source}")
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.85 # زيادة الإبداع للمحتوى الطويل
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ في توليد المحتوى: {e}")
        return None

def publish_long_tweet():
    logging.info("🚀 بدء تحضير المقال التقني الطويل...")
    content = generate_premium_analysis()
    
    if not content: return

    try:
        # الاتصال بـ API V2 لدعم التغريدات الطويلة للمشتركين
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # في حسابات بريميوم، سيقوم نظام X بمعالجة هذا النص كـ Long Tweet تلقائياً
        response = client.create_tweet(text=content)
        
        if response:
            logging.info(f"✅ تم نشر المقال بنجاح! الرابط: https://x.com/i/status/{response.data['id']}")
            
    except Exception as e:
        logging.error(f"❌ فشل النشر (تحقق من صلاحيات Write): {e}")

if __name__ == "__main__":
    publish_long_tweet()
