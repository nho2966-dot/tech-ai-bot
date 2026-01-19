import os
import tweepy
import logging
import re
from google import genai

logging.basicConfig(level=logging.INFO)

def generate_reply(text):
    # رد مبدئي ذكي، يمكن ربطه بـ Gemini لاحقاً
    return f"تحليل تقني رائع! شكراً لإضافتك القيمة. 🚀\nGreat tech insight! Thanks for sharing."

def run_reply_agent():
    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
        )
        
        me = client.get_me().data
        if not me: return

        # جلب المنشن (الإشارات)
        mentions = client.get_users_mentions(id=me.id, max_results=5)
        
        if not mentions.data:
            logging.info("😴 لا توجد إشارات جديدة.")
            return

        for tweet in mentions.data:
            reply_text = generate_reply(tweet.text)
            client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
            logging.info(f"✅ تم الرد على: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ في الردود: {e}")

# لمنع أخطاء الاستيراد
process_mentions = run_reply_agent

if __name__ == "__main__":
    run_reply_agent()
