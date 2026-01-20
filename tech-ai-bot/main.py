import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# دالة مركزية للاتصال لضمان توحيد الصلاحيات
def get_client():
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )

def generate_ai_content(prompt):
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.3
            }, timeout=20
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except:
        return None

def auto_post():
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    prompt = f"اكتب تغريدة تقنية احترافية بالعربية عن خبر من {source}. الهيكل: 🛡️ التقنية، 💡 الأهمية، 🛠️ التوظيف، 🌍 المصدر: {source}. أضف وسم #تقنية."
    
    content = generate_ai_content(prompt)
    if content:
        try:
            client = get_client()
            # النشر بنظام V2 الذي نجحنا به سابقاً
            client.create_tweet(text=content[:280])
            logging.info("✅ تم النشر التلقائي بنجاح!")
        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")

def handle_mentions():
    logging.info("🔍 محاولة فحص الإشارات...")
    try:
        client = get_client()
        me = client.get_me()
        if not me.data: return
        
        # جلب المنشنز مع معالجة الخطأ إذا كان الحساب لا يدعم القراءة
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        
        if mentions.data:
            for tweet in mentions.data:
                reply_prompt = f"أجب باختصار تقني جداً على: {tweet.text}"
                reply_text = generate_ai_content(reply_prompt)
                if reply_text:
                    client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                    logging.info(f"✅ تم الرد على {tweet.id}")
    except Exception as e:
        logging.warning(f"⚠️ نظام الرد غير متاح حالياً (قد يتطلب ترقية الحساب): {e}")

if __name__ == "__main__":
    # تشغيل النشر أولاً لأنه الأولوية التي نجحت سابقاً
    auto_post()
    # محاولة الرد بشكل منفصل بحيث لا يؤثر فشلها على النشر
    handle_mentions()
