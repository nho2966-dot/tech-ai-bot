import os
import tweepy
from google import genai  # الاستيراد الصحيح للمكتبة الجديدة
from datetime import datetime, timezone, timedelta
import logging

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_reply_bot():
    """تهيئة عميل X بصلاحية القراءة والكتابة (OAuth 1.0a)"""
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )

def generate_smart_reply(question: str) -> str:
    """توليد رد ذكي باستخدام مكتبة google-genai الجديدة"""
    # تهيئة العميل للمكتبة الجديدة
    client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))
    
    prompt = (
        "أنت بوت تقني ذكي ومهذب اسمك 'تيك بوت'.\n"
        "أجب عن السؤال التالي بإيجاز، بالعربية الفصحى، "
        "بأسلوب محترف.\n\n"
        f"السؤال: {question}"
    )
    
    try:
        # الطريقة الصحيحة للاستدعاء في المكتبة الجديدة
        response = client_ai.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        reply = response.text.strip()
        return reply[:270]
    except Exception as e:
        logging.error(f"فشل توليد الرد من Gemini: {e}")
        return "شكرًا لسؤالك! أتعلم المزيد حالياً وسأرد فور جاهزيتي. 🤖✨"

def process_mentions(bot_username: str):
    client = get_reply_bot()

    try:
        user = client.get_me()
        user_id = user.data.id
        logging.info(f"تم الاتصال بحساب: @{user.data.username}")
    except Exception as e:
        logging.error(f"فشل المصادقة مع X API: {e}")
        return

    try:
        mentions = client.get_users_mentions(
            id=user_id,
            max_results=10,
            tweet_fields=["created_at"]
        )
    except Exception as e:
        logging.error(f"فشل جلب التغريدات الموجهة: {e}")
        return

    # تصحيح: إضافة .data للتحقق من وجود تغريدات
    if not mentions or not mentions.data:
        logging.info("لا توجد تغريدات موجهة جديدة.")
        return

    for mention in mentions.data:
        # تصحيح: السماح بفترة أطول قليلاً (ساعتين) لتجنب السجلات الفارغة
        if (datetime.now(timezone.utc) - mention.created_at) > timedelta(hours=2):
            continue

        tweet_text = mention.text
        logging.info(f"معالجة تغريدة: {tweet_text}")

        # استخراج السؤال
        question = tweet_text.lower().replace(f"@{bot_username.lower()}", "").strip()
        if not question:
            continue

        reply_text = generate_smart_reply(question)

        try:
            client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=mention.id
            )
            logging.info(f"✅ تم الرد بنجاح على: {mention.id}")
        except Exception as e:
            logging.error(f"❌ فشل نشر الرد: {e}")

if __name__ == "__main__":
    # تأكد من وضع اسم الحساب الصحيح في الـ Secrets
    username = os.getenv("BOT_USERNAME", "TechAI_Bot")
    process_mentions(username)
