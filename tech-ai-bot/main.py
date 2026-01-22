import os
import tweepy
import requests
import logging
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

# إعداد الاتصال بـ X API V2
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

def get_ai_content(prompt):
    """دالة التواصل مع AI لجلب المحتوى والردود"""
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.85
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ AI: {e}")
        return None

def generate_youth_trend():
    """توليد محتوى ترند شبابي طويل"""
    topics = [
        "أخبار ألعاب الفيديو وأجهزة القيمنق والـ PC",
        "طرق ذكية لاستخدام الذكاء الاصطناعي في الدراسة والعمل الحر",
        "مراجعة لأحدث الهواتف والتقنيات القابلة للارتداء",
        "مستقبل شبكات التواصل الاجتماعي وأخبار منصة X"
    ]
    topic = random.choice(topics)
    prompt = (
        f"اكتب مقالاً تقنياً طويلاً (850 حرف) بأسلوب فصيح وشبابي عن {topic}.\n"
        "ابدأ بعبارة جذابة، وقدم فائدة عملية.\n"
        "#تقنية #شباب_عُمان #الذكاء_الاصطناعي #ترند_اليوم"
    )
    return get_ai_content(prompt)

def reply_to_mentions():
    """نظام الردود التلقائية"""
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        
        if not mentions.data:
            logging.info("ℹ️ لا توجد تعليقات جديدة للرد عليها.")
            return

        for tweet in mentions.data:
            logging.info(f"💬 جاري الرد على التعليق: {tweet.id}")
            reply_prompt = f"اكتب رداً ودوداً وقصيراً وفصيحاً على هذا التعليق: {tweet.text}"
            reply_text = get_ai_content(reply_prompt)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد بنجاح!")
    except Exception as e:
        logging.info(f"ℹ️ تنبيه في الردود (قد لا توجد صلاحيات كافية للبعض): {e}")

def run_bot():
    logging.info("🤖 بدء تشغيل المحلل التقني (نسخة Premium)...")
    try:
        # فحص الهوية
        me = client.get_me()
        if me.data:
            logging.info(f"✅ متصل بنجاح كـ: {me.data.username}")
            
            # 1. الرد على التعليقات
            reply_to_mentions()
            
            # 2. النشر الرئيسي
            content = generate_youth_trend()
            if content:
                client.create_tweet(text=content)
                logging.info("🔥 تم نشر مقال الترند الطويل بنجاح!")
    except Exception as e:
        logging.error(f"❌ فشل عام: {e}")

if __name__ == "__main__":
    run_bot()
