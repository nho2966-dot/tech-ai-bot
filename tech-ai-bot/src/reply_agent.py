import os
import tweepy
import logging
import re
from google import genai

logging.basicConfig(level=logging.INFO)

def run_reply_agent():
    """الرد على المنشن باستخدام المفاتيح الأربعة فقط."""
    try:
        # استخدام OAuth 1.0a (المفاتيح الأربعة)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
        )
        
        me = client.get_me().data
        if not me: return

        # جلب التنبيهات (الردود)
        mentions = client.get_users_mentions(id=me.id, max_results=10)
        
        if not mentions.data:
            logging.info("😴 لا توجد إشارات جديدة.")
            return

        for tweet in mentions.data:
            # دالة توليد الرد (تستخدم Gemini)
            reply_text = "شكراً لتفاعلك! نحن هنا لدعم رحلتك التقنية. 🚀" 
            
            client.create_tweet(
                text=reply_text[:280],
                in_reply_to_tweet_id=tweet.id
            )
            logging.info(f"✅ تم الرد على: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ في الردود: {e}")

# لضمان عدم حدوث ImportError في main.py
process_mentions = run_reply_agent

if __name__ == "__main__":
    run_reply_agent()
