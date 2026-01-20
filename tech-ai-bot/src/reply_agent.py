import os
import tweepy
import google.genai as genai
from google.genai import types
import logging
from datetime import datetime, timezone

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_twitter_clients():
    """تهيئة V1.1 للقراءة و V2 للنشر باستخدام المفاتيح الأربعة فقط."""
    auth = tweepy.OAuth1UserHandler(
        os.getenv("X_API_KEY"),
        os.getenv("X_API_SECRET"),
        os.getenv("X_ACCESS_TOKEN"),
        os.getenv("X_ACCESS_SECRET")
    )
    api = tweepy.API(auth)
    
    client = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )
    return api, client

def generate_smart_reply(question: str) -> str:
    """توليد رد ذكي باستخدام Gemini 2.0 Flash."""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        prompt = (
            "أنت بوت تقني ذكي اسمه 'تيك بوت'. أجب عن السؤال التالي بإيجاز شديد (جملة واحدة)، "
            "بالعربية الفصحى، بأسلوب محترف ومفيد.\n\n"
            f"السؤال: {question}"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        reply = response.text.strip()
        return reply[:280]
    except Exception as e:
        logging.error(f"فشل Gemini: {e}")
        return "شكرًا لسؤالك! سأبحث في هذا الموضوع وأرد عليك لاحقاً. 🤖✨"

def run_reply_agent():
    bot_username = os.getenv("BOT_USERNAME", "TechAI_Bot")
    api, client = get_twitter_clients()

    try:
        # جلب المنشن باستخدام V1.1 (أكثر استقراراً بالمفاتيح الأربعة)
        mentions = api.mentions_timeline(count=10, tweet_mode='extended')
        if not mentions:
            logging.info("لا توجد تغريدات موجهة جديدة.")
            return

        for tweet in mentions:
            # تجاهل التغريدات الأقدم من 15 دقيقة (لتجنب التكرار في الأكشن)
            time_diff = datetime.now(timezone.utc) - tweet.created_at.replace(tzinfo=timezone.utc)
            if time_diff.total_seconds() > 900: # 15 دقيقة
                continue

            question = tweet.full_text.replace(f"@{bot_username}", "").strip()
            if not question: continue

            logging.info(f"معالجة سؤال من @{tweet.user.screen_name}: {question}")
            
            reply_text = f"@{tweet.user.screen_name} {generate_smart_reply(question)}"
            
            # الرد باستخدام V2 Client (الطريقة التي نجحت معك سابقاً)
            client.create_tweet(
                text=reply_text[:280],
                in_reply_to_tweet_id=tweet.id
            )
            logging.info(f"✅ تم الرد على {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ في النظام: {e}")

if __name__ == "__main__":
    run_reply_agent()
