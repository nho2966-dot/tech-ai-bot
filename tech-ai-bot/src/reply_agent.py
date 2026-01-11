import os
import tweepy
import genai from google
import logging

def process_mentions(username):
    try:
        # الاتصال بـ Gemini و Twitter باستخدام الأسرار المحددة في إعداداتك
        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        bot_id = client.get_me().data.id
        mentions = client.get_users_mentions(id=bot_id, max_results=5)

        if not mentions.data:
            logging.info("لا توجد إشارات جديدة للرد عليها.")
            return

        for tweet in mentions.data:
            prompt = f"رد على هذه التغريدة بأسلوب تقني ذكي وقصير جداً بالعربية: {tweet.text}"
            response = client_ai.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            
            client.create_tweet(text=response.text[:280], in_reply_to_tweet_id=tweet.id)
            logging.info(f"✅ تم الرد على التغريدة رقم: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ في نظام الردود: {e}")

