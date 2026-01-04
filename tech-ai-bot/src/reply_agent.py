import os
import tweepy
from google import genai
from datetime import datetime, timezone, timedelta
import logging

# إعداد نظام التسجيل (Logs) ليظهر كل شيء في GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_reply_bot():
    """الاتصال بـ X باستخدام كافة المفاتيح المطلوبة لصلاحية الكتابة"""
    logging.info("محاولة الاتصال بمنصة X...")
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
        "أنت بوت تقني محترف وودود اسمك 'تيك بوت'.\n"
        "أجب عن السؤال التالي باختصار شديد (جملة أو جملتين)، بالعربية الفصحى.\n"
        "اجعل إجابتك مفيدة وتقنية.\n\n"
        f"السؤال: {question}"
    )
    
    try:
        response = client_ai.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        reply = response.text.strip()
        # تويتر يسمح بـ 280 حرف، نقتطع النص إذا زاد
        return reply[:270] + ".." if len(reply) > 280 else reply
    except Exception as e:
        logging.error(f"خطأ في توليد الرد من Gemini: {e}")
        return "شكراً لسؤالك! سأبحث في هذا الأمر وأرد عليك قريباً. 🤖"

def process_mentions(bot_username: str):
    client = get_reply_bot()
    
    try:
        # التحقق من هوية البوت
        me = client.get_me()
        user_id = me.data.id
        logging.info(f"تم تسجيل الدخول بنجاح باسم الحساب: @{me.data.username}")
    except Exception as e:
        logging.error(f"فشل الاتصال بتويتر. تأكد من إعدادات OAuth 1.0a وSecrets: {e}")
        return

    logging.info("البحث عن التغريدات الموجهة (Mentions)...")
    try:
        # جلب المنشن (آخر 10 تغريدات)
        mentions = client.get_users_mentions(
            id=user_id,
            max_results=10,
            tweet_fields=["created_at", "author_id"]
        )
    except Exception as e:
        logging.error(f"فشل جلب التغريدات: {e}")
        return

    if not mentions or not mentions.data:
        logging.info("لا توجد تغريدات جديدة حالياً.")
        return

    for mention in mentions.data:
        # معالجة التغريدات التي وصلت خلال آخر 24 ساعة (لتجنب الـ Logs الفارغة)
        time_diff = datetime.now(timezone.utc) - mention.created_at
        if time_diff > timedelta(hours=24):
            continue

        logging.info(f"جاري معالجة تغريدة من ID: {mention.author_id}")
        
        # تنظيف النص من اسم البوت
        tweet_text = mention.text
        question = tweet_text.lower().replace(f"@{bot_username.lower()}", "").strip()
        
        # توليد الرد
        reply_text = generate_smart_reply(question)

        try:
            # نشر الرد على تويتر
            client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=mention.id
            )
            logging.info(f"✅ تم الرد بنجاح على التغريدة رقم: {mention.id}")
        except Exception as e:
            logging.error(f"❌ فشل نشر التغريدة: {e}")

if __name__ == "__main__":
    # استلام اسم البوت من متغيرات البيئة أو استخدام الافتراضي
    BOT_NAME = os.getenv("BOT_USERNAME", "TechAI_Bot")
    process_mentions(BOT_NAME)
