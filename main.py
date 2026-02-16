import os
import logging
import time
from google import genai  # مكتبة Gemini
import openai
import tweepy

# إعدادات Logging
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# ==== 1. إعداد مفاتيح البيئة ====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # JSON

# ==== 2. إعداد عملاء الذكاء الاصطناعي ====

# Gemini (Google GenAI)
gemini_client = genai.GenAIClient()

# OpenAI
openai.api_key = OPENAI_API_KEY

# Tweepy
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
)
twitter_client = tweepy.API(auth)

# ==== 3. دوال استدعاء الذكاء الاصطناعي ====
def call_gemini(prompt):
    """استدعاء Gemini (Google GenAI)"""
    try:
        response = gemini_client.generate_text(
            model="gemini-2.0-flash",
            prompt=prompt
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return None

def call_openai(prompt):
    """استدعاء OpenAI GPT"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return None

# ==== 4. دالة نشر التغريدة ====
def post_tweet(text):
    try:
        twitter_client.update_status(text)
        logging.info("تم نشر التغريدة بنجاح ✅")
    except Exception as e:
        logging.error(f"Twitter error: {e}")

# ==== 5. التشغيل الرئيسي ====
if __name__ == "__main__":
    prompt = "اكتب تغريدة جذابة عن أحدث أخبار الذكاء الاصطناعي."
    
    # تجربة Gemini أولاً
    tweet_text = call_gemini(prompt)
    
    # إذا فشل Gemini جرب OpenAI
    if not tweet_text:
        tweet_text = call_openai(prompt)
    
    if tweet_text:
        post_tweet(tweet_text)
    else:
        logging.error("فشل في توليد التغريدة من كلا الخدمتين ❌")
