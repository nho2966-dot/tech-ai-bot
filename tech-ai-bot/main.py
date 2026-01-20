import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )

# 2. توليد المحتوى (للنشر أو للرد)
def generate_ai_response(prompt):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
        payload = {
            "model": "meta-llama/llama-3.1-70b-instruct",
            "messages": [{"role": "system", "content": "أنت خبير تقني تجيب بدقة واختصار."}, {"role": "user", "content": prompt}],
            "temperature": 0.4
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=25)
        return res.json()['choices'][0]['message']['content'].strip()
    except:
        return None

# 3. وظيفة النشر التلقائي (المصادر الموثوقة + الوسوم)
def auto_post():
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    prompt = f"اكتب تغريدة تقنية احترافية بالعربية عن خبر من {source}. الهيكل: 🛡️ التقنية، 💡 الأهمية، 🛠️ التوظيف، 🌍 المصدر: {source}. أضف وسم #تقنية."
    
    content = generate_ai_response(prompt)
    if content:
        try:
            client = get_twitter_client()
            client.create_tweet(text=content[:280])
            logging.info("✅ تم النشر التلقائي بنجاح!")
        except Exception as e:
            logging.error(f"❌ فشل النشر التلقائي: {e}")

# 4. وظيفة الرد الآلي (Auto-Reply)
def handle_mentions():
    logging.info("🔍 فحص الإشارات (Mentions) للرد عليها...")
    client = get_twitter_client()
    
    try:
        # جلب معرف البوت أولاً
        me = client.get_me()
        my_id = me.data.id
        
        # جلب المنشنز (آخر 5 فقط لتجنب استهلاك الكوتا في الحساب المجاني)
        mentions = client.get_users_mentions(id=my_id, max_results=5)
        
        if not mentions.data:
            logging.info("ℹ️ لا توجد إشارات جديدة.")
            return

        for tweet in mentions.data:
            # هنا يمكنك إضافة نظام لمنع الرد على نفس التغريدة مرتين (عن طريق حفظ الـ ID)
            reply_prompt = f"اكتب رداً تقنياً مختصراً جداً بالعربية على هذا الاستفسار: {tweet.text}"
            reply_text = generate_ai_response(reply_prompt)
            
            if reply_text:
                client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد على التغريدة: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ فشل نظام الرد: {e}")

if __name__ == "__main__":
    auto_post()      # أولاً ينشر الخبر الجديد
    handle_mentions() # ثم يرد على المستفسرين
