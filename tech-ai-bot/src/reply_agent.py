import os
import tweepy
import google.genai as genai
import logging

logging.basicConfig(level=logging.INFO)

def run_reply_agent():
    try:
        # استخدام V2 حصراً للقراءة والرد
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id)
        
        if not mentions.data:
            return

        ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        for tweet in mentions.data:
            # هنا نضع رد Gemini أو كوين
            response = ai_client.models.generate_content(model="gemini-2.0-flash", contents=tweet.text)
            client.create_tweet(text=response.text[:280], in_reply_to_tweet_id=tweet.id)
            logging.info("✅ تم الرد بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ الردود: {e}")

if __name__ == "__main__":
    run_reply_agent()
