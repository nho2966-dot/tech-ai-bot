import os
import requests
import tweepy
import random
from google import genai
import logging

def generate_tech_content():
    try:
        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        tavily_key = os.getenv("TAVILY_KEY")
        
        # البحث عن خبر تقني
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": "new AI tools and tech news 2026",
                "max_results": 1
            }, timeout=10
        )
        res_data = response.json()
        raw_info = res_data['results'][0]['content']
        source_url = res_data['results'][0]['url']

        prompt = f"لخص هذا الخبر في جملة تقنية عربية مشوقة جداً لتغريدة: {raw_info}"
        
        gemini_res = client_ai.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return gemini_res.text.strip(), source_url
    except Exception as e:
        logging.error(f"خطأ في توليد المحتوى: {e}")
        return None, None

def publish_tech_tweet():
    content, url = generate_tech_content()
    if not content: return

    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
        )
        tweet = f"🛡️ حصري | {content}\n\n🔗 {url}\n#تيك_بوت #تقنية"
        client.create_tweet(text=tweet)
        logging.info("✅ تم نشر التغريدة.")
    except Exception as e:
        logging.error(f"خطأ في النشر: {e}")
