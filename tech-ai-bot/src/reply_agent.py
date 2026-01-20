import os
import tweepy
import google.genai as genai
import logging
from datetime import datetime, timezone

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_twitter_client():
    """التهيئة باستخدام V2 Client والمفاتيح الأربعة فقط."""
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
        wait_on_rate_limit=True
    )

def generate_smart_reply(question: str) -> str:
    """توليد رد ذكي باستخدام Gemini 2.0 Flash."""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        prompt = (
            "أنت بوت تقني ذكي ومهذب اسمه 'تيك بوت'.\n"
            "أجب عن السؤال التالي بإيجاز شديد (جملة واحدة فقط)، بالعربية الفصحى، "
            "بأسلوب محترف، ولا تكرر السؤال.\n\n"
            f"السؤال: {question}"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        reply = response.text.strip()
        return reply[:280]
    except Exception as e:
        logging.error(f"فشل توليد الرد من Gemini: {e}")
        return "شكرًا لسؤالك! سأبحث في هذا الموضوع وأرد عليك قريباً. 🤖"

def run_reply_agent():
    bot_username = os.getenv("BOT_USERNAME", "TechAI_Bot")
    client = get_twitter_client()

    try:
        # 1. التحقق من المصادقة وجلب ID البوت
        me = client.get_me()
        if not me.data:
            logging.error("❌ فشل في جلب بيانات الحساب.")
            return
        
        user_id = me.data.id
        logging.info(f"✅ تم الاتصال بحساب: @{me.data.username}")

        # 2. جلب المنشن (الإشارات) باستخدام V2
        # ملاحظة: max_results يجب أن تكون بين 5 و 100
        mentions = client.get_users_mentions(id=user_id, max_results=5)
        
        if not mentions.data:
            logging.info("😴 لا توجد تغريدات موجهة جديدة.")
            return

        for tweet in mentions.data:
            # تنظيف السؤال من اسم البوت
            question = tweet.text.replace(f"@{bot_username}", "").strip()
            if not question:
                continue

            logging.info(f"🔍 معالجة منشن من {tweet.author_id}: {question}")
            
            # توليد الرد
            reply_content = generate_smart_reply(question)
            
            # 3. نشر الرد (باستخدام الطريقة التي نجحت معك سابقاً)
            client.create_tweet(
                text=reply_content,
                in_reply_to_tweet_id=tweet.id
            )
            logging.info(f"✅ تم الرد بنجاح على التغريدة ID: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ في النظام: {e}")

if __name__ == "__main__":
    run_reply_agent()
