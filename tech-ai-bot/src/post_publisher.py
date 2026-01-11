import os
import requests
import tweepy
from google import genai
import logging

def publish_tech_tweet():
    try:
        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        
        # البحث عن خبر (يمكنك استخدام Tavily هنا إذا أردت)
        prompt = "أعطني معلومة تقنية مذهلة وجديدة عن الذكاء الاصطناعي في عام 2026 لتغريدة عربية مشوقة مع هاشتاقات."
        
        response = client_ai.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        tweet_text = response.text.strip()

        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        client.create_tweet(text=tweet_text[:280])
        logging.info("✅ تم نشر التغريدة التقنية بنجاح.")

    except Exception as e:
        logging.error(f"❌ خطأ في نظام النشر: {e}")
