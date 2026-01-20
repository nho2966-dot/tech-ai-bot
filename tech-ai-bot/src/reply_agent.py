import os
import tweepy
import google.genai as genai
import logging

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO)

def run_reply_agent():
    # 1. تهيئة Gemini (تأكد من وجود GEMINI_KEY في السكرت)
    gemini_key = os.getenv("GEMINI_KEY")
    ai_client = genai.Client(api_key=gemini_key)

    # 2. تهيئة تويتر بنظام V1.1 (الوضع السابق الناجح)
    auth = tweepy.OAuth1UserHandler(
        os.getenv("X_API_KEY"),
        os.getenv("X_API_SECRET"),
        os.getenv("X_ACCESS_TOKEN"),
        os.getenv("X_ACCESS_SECRET")
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)

    try:
        # جلب المنشن - V1.1 تعمل جيداً بالمفاتيح الأربعة
        mentions = api.mentions_timeline(count=5, tweet_mode='extended')
        
        if not mentions:
            logging.info("لا توجد منشنات جديدة.")
            return

        for tweet in mentions:
            # صياغة الرد عبر Gemini
            prompt = f"رد باختصار جداً على هذه التغريدة: {tweet.full_text}"
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            reply_text = f"@{tweet.user.screen_name} {response.text.strip()}"
            
            # النشر بالوضع السابق الموثوق
            api.update_status(
                status=reply_text[:280],
                in_reply_to_status_id=tweet.id
            )
            logging.info(f"✅ تم الرد بنجاح على: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ فشل في الوضع السابق: {e}")

if __name__ == "__main__":
    run_reply_agent()
