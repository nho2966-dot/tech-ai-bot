import os
import tweepy
import google.genai as genai
import requests
import logging
import random

logging.basicConfig(level=logging.INFO)

def get_content_from_openrouter():
    """الخيار الاحتياطي: كوين (OpenRouter) في حال نفاد حصة جمناي."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "اكتب تغريدة تقنية قصيرة ومفيدة عن الذكاء الاصطناعي بالعربية."}]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ فشل كوين أيضاً: {e}")
        return "الذكاء الاصطناعي يغير العالم يوماً بعد يوم. 🚀"

def generate_content():
    """المحاولة الأولى مع جمناي، وإذا فشل ننتقل لكوين."""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="اكتب تغريدة تقنية قصيرة ومفيدة عن الذكاء الاصطناعي بالعربية."
        )
        return response.text.strip()
    except Exception:
        logging.warning("⚠️ نفدت حصة جمناي.. الانتقال إلى كوين (OpenRouter)...")
        return get_content_from_openrouter()

def publish_tweet():
    try:
        # استخدام V2 حصراً لتفادي خطأ 403
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        content = generate_content()
        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ نهائي في النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
