import os
import tweepy
import google.genai as genai
import requests
import logging

logging.basicConfig(level=logging.INFO)

def get_content_from_openrouter(prompt):
    """استخدام كوين كخيار احتياطي لضمان جودة المحتوى."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ فشل كوين: {e}")
        return None

def generate_professional_content():
    """توليد محتوى بنمط تغريدة LTPO."""
    prompt = (
        "اكتب تغريدة تقنية احترافية باللغة العربية.\n"
        "التنسيق: 1. التقنية، 2. الأهمية، 3. التوظيف، 4. المصدر.\n"
        "اجعلها دقيقة تقنياً ومختصرة."
    )
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except:
        logging.warning("⚠️ جمناي مستنفد، جاري طلب المحتوى من كوين...")
        return get_content_from_openrouter(prompt)

def publish_tweet():
    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False # لمنع التعليق الطويل
        )
        content = generate_professional_content()
        if content:
            client.create_tweet(text=content[:280])
            logging.info("✅ تم النشر الاحترافي بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
