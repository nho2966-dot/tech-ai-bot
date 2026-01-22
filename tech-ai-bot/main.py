import os
import tweepy
import requests
import logging
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

# إعداد الـ Client مع دعم كامل لميزات البريميوم
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

def run_bot():
    logging.info("🤖 بدء فحص الاتصال بالهوية الجديدة...")
    try:
        # التحقق من نجاح المصادقة
        me = client.get_me()
        if me.data:
            logging.info(f"✅ متصل بنجاح كـ: {me.data.username}")
            
            # تنفيذ الردود على المنشنز
            reply_to_mentions()
            
            # تنفيذ النشر الرئيسي (مقال الترند)
            content = generate_youth_trend()
            if content:
                client.create_tweet(text=content)
                logging.info("🔥 تم نشر مقال الترند بنجاح!")
        else:
            logging.error("❌ فشل الحصول على بيانات الحساب.")
    except Exception as e:
        logging.error(f"❌ فشل في المصادقة: {e}")

# ... استكمل بقية الدوال (generate_youth_trend و reply_to_mentions) كما في الكود السابق ...

if __name__ == "__main__":
    run_bot()
