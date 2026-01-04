import os
import tweepy
from google import genai  # المكتبة الجديدة
from datetime import datetime, timezone
import logging
import hashlib

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_reply_bot():
    """إرجاع عميل X مع صلاحيات الكتابة الكاملة باستخدام OAuth 1.0a"""
    return tweepy.Client(
        bearer_token=os.getenv('X_BEARER_TOKEN'),
        consumer_key=os.getenv('X_API_KEY'),
        consumer_secret=os.getenv('X_API_SECRET'),
        access_token=os.getenv('X_ACCESS_TOKEN'),
        access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
    )

def generate_smart_reply(question: str) -> str:
    """استخدم Gemini 2.0 لإنشاء رد احترافي"""
    # إعداد عميل Gemini الجديد
    client_ai = genai.Client(api_key=os.getenv('GEMINI_KEY'))
    
    prompt = (
        "أنت بوت تقني ذكي ومهذب اسمك 'تيك بوت'.\n"
        "أجب عن السؤال التالي بإيجاز (لا تتجاوز جملتين)، بالعربية الفصحى، "
        "بأسلوب ودود ومحترف، ولا تكرر السؤال.\n\n"
        f"السؤال: {question}"
    )
    
    try:
        # استخدام موديل Flash 2.0 السريع
        response = client_ai.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        reply = response.text.strip()
        # التأكد من طول التغريدة (تويتر يسمح بـ 280 حرف)
        return reply[:275] if len(reply) > 280 else reply
    except Exception as e:
        logging.error(f"فشل توليد الرد: {e}")
        return "شكرًا لسؤالك! أعمل حالياً على معالجة طلبك تقنياً. 🤖✨"

def process_mentions(bot_username: str):
    client = get_reply_bot()
    
    try:
        # جلب معرف البوت (User ID)
        user = client.get_me()
        user_id = user.data.id
        logging.info(f"تم تسجيل الدخول بنجاح كـ: {user.data.username}")
    except Exception as e:
        logging.error(f"فشل جلب معلومات الحساب (تأكد من المفاتيح): {e}")
        return

    try:
        # جلب المنشن (آخر 10 تغريدات)
        mentions = client.get_users_mentions(
            id=user_id,
            max_results=10,
            tweet_fields=["created_at", "author_id"]
        )
    except Exception as e:
        logging.error(f"فشل جلب التغريدات الموجهة: {e}")
        return

    if not mentions or not mentions.data:
        logging.info("لا توجد تغريدات موجهة جديدة.")
        return

    for mention in mentions.data:
        # معالجة التغريدات التي لم يمر عليها أكثر من ساعة
        created_at = mention.created_at
        if (datetime.now(timezone.utc) - created_at).total_seconds() > 3600:
            continue

        tweet_text = mention.text
        logging.info(f"يتم الآن معالجة: {tweet_text}")

        # تنظيف النص من اسم البوت للحصول على السؤال
        question = tweet_text.lower().replace(f"@{bot_username.lower()}", "").strip()
        
        if not question:
            reply_text = "مرحباً! أنا تيك بوت، كيف يمكنني مساعدتك تقنياً اليوم؟ 🤖"
        else:
            reply_text = generate_smart_reply(question)

        try:
            # الرد على التغريدة
            client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=mention.id
            )
            logging.info(f"✅ تم الرد بنجاح على التغريدة: {mention.id}")
        except Exception as e:
            logging.error(f"❌ فشل نشر الرد: {e}")

if __name__ == "__main__":
    # تأكد من وضع اسم حساب البوت بدون @ هنا
    BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername") 
    process_mentions(BOT_USERNAME)
