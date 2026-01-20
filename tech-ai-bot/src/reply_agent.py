import os
import tweepy
import google.genai as genai
import logging

logging.basicConfig(level=logging.INFO)

def run_reply_agent():
    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False
        )
        
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id)
        
        if not mentions.data:
            logging.info("لا توجد منشنات.")
            return

        ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        for tweet in mentions.data:
            response = ai_client.models.generate_content(model="gemini-2.0-flash", contents=tweet.text)
            client.create_tweet(text=f"{response.text[:270]}", in_reply_to_tweet_id=tweet.id)
            logging.info(f"✅ تم الرد على {tweet.id}")
            
    except Exception as e:
        logging.error(f"❌ خطأ الردود: {e}")

if __name__ == "__main__":
    run_reply_agent()
