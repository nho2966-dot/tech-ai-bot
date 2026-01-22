import os
import tweepy
import requests
import logging
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv

# إعدادات التسجيل لضمان الـوُضُـوح في تتبع العمليات
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

def is_golden_hour():
    """توقيت مسقط - النشر في ساعات الذروة فقط"""
    oman_tz = pytz.timezone('Asia/Muscat')
    now_oman = datetime.now(oman_tz)
    hour = now_oman.hour
    # الساعات الذهبية: 10 ص - 2 ظهراً ومن 8 مساءً - 11 مساءً
    return hour in [10, 11, 12, 13, 14, 20, 21, 22, 23]

def get_ai_content(prompt):
    """دالة موحدة لجلب المحتوى من OpenRouter"""
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
        logging.error(f"❌ خطأ في AI: {e}")
        return None

def generate_youth_trend():
    """توليد محتوى ترند يستهدف الشباب"""
    topics = [
        "أخبار GTA VI وتسريبات القيمنق وأجهزة الـ PC",
        "كيفية استخدام AI لكسب المال والعمل الحر (Freelancing)",
        "أحدث صيحات الهواتف الذكية والتطبيقات التي تسهل حياة الطلاب",
        "تحديثات X و Grok AI وكيفية تصدر الترند"
    ]
    topic = random.choice(topics)
    prompt = (
        f"اكتب مقالاً تقنياً طويلاً (900 حرف) بأسلوب شبابي وفصيح عن {topic}.\n"
        "ابدأ بجملة خاطفة (Hook)، حلل الخبر، وقدم فائدة مباشرة للشاب العُماني والعربي.\n"
        "استخدم الرموز التعبيرية بحرفية.\n"
        "#تقنية #شباب_عُمان #الذكاء_الاصطناعي #ترند_اليوم"
    )
    return get_ai_content(prompt)

def reply_to_mentions():
    """نظام الردود الذكية على المتابعين"""
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        
        if not mentions.data:
            logging.info("ℹ️ لا توجد منشنز جديدة.")
            return

        for tweet in mentions.data:
            logging.info(f"💬 الرد على المنشن: {tweet.id}")
            reply_prompt = f"رد بشكل ذكي وفصيح وقصير جداً على هذا المستخدم الذي يقول: {tweet.text}"
            reply_text = get_ai_content(reply_prompt)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد على {tweet.id}")
    except Exception as e:
        logging.error(f"❌ خطأ في الردود: {e}")

def run_bot():
    logging.info("🤖 بدء تشغيل المحلل التقني (نسخة Premium)...")
    
    # 1. الرد على التعليقات (تعمل دائماً لضمان التفاعل)
    reply_to_mentions()
    
    # 2. النشر الرئيسي (يعمل فقط في الساعات الذهبية للـوُضُـوح والانتشار)
    if is_golden_hour():
        content = generate_youth_trend()
        if content:
            try:
                client.create_tweet(text=content)
                logging.info("🔥 تم نشر مقال الترند الطويل بنجاح!")
            except Exception as e:
                logging.error(f"❌ خطأ في النشر: {e}")

if __name__ == "__main__":
    run_bot()
