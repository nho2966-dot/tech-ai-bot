import os
import tweepy
from google import genai
from datetime import datetime, timezone, timedelta
import logging

# إعداد التسجيل لرؤية النتائج في GitHub Actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_reply_bot():
    """الاتصال بـ X مع صلاحيات الكتابة الكاملة"""
    # لا يمكن النشر باستخدام Bearer Token وحده؛ يجب استخدام المفاتيح الأربعة
    return tweepy.Client(
        bearer_token=os.getenv('X_BEARER_TOKEN'),
        consumer_key=os.getenv('X_API_KEY'),
        consumer_secret=os.getenv('X_API_SECRET'),
        access_token=os.getenv('X_ACCESS_TOKEN'),
        access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
    )

def generate_smart_reply(question: str) -> str:
    """توليد رد ذكي باستخدام Gemini 2.0 Flash"""
    client_ai = genai.Client(api_key=os.getenv('GEMINI_KEY'))
    
    prompt = (
        "أنت بوت تقني ذكي ومهذب اسمك 'تيك بوت'. "
        "أجب عن السؤال التالي بإيجاز شديد (جملة واحدة)، بالعربية الفصحى، "
        "بأسلوب محترف.\n\n"
        f"السؤال: {question}"
    )
    
    try:
        response = client_ai.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        reply = response.text.strip()
        return reply[:270] # تويتر يسمح بـ 280 حرف كحد أقصى
    except Exception as e:
        logging.error(f"خطأ في توليد الرد: {e}")
        return "شكراً لتواصلك! سأقوم بالرد عليك قريباً. 🤖"

def process_mentions(bot_username: str):
    client = get_reply_bot()
    
    try:
        me = client.get_me()
        user_id = me.data.id
        logging.info(f"تم تسجيل الدخول بنجاح كـ @{me.data.username}")
    except Exception as e:
        logging.error(f"فشل الاتصال: {e}")
        return

    # جلب المنشنات الجديدة
    mentions = client.get_users_mentions(id=user_id, max_results=10, tweet_fields=["created_at"])

    if not mentions or not mentions.data:
        logging.info("لا توجد منشنات جديدة للرد عليها.")
        return

    for mention in mentions.data:
        # فحص الوقت (آخر 24 ساعة لضمان عدم وجود سجلات فارغة)
        if (datetime.now(timezone.utc) - mention.created_at) > timedelta(hours=24):
            continue

        question = mention.text.lower().replace(f"@{bot_username.lower()}", "").strip()
        reply_text = generate_smart_reply(question)

        try:
            client.create_tweet(text=reply_text, in_reply_to_tweet_id=mention.id)
            logging.info(f"✅ تم الإرسال بنجاح للتغريدة ID: {mention.id}")
        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    BOT_NAME = os.getenv("BOT_USERNAME", "TechAI_Bot")
    process_mentions(BOT_NAME)
