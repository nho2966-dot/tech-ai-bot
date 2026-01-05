import os
import tweepy
import google.genai as genai
from datetime import datetime, timezone
import logging
import hashlib

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# تهيئة Gemini API
genai.configure(api_key=os.getenv("GEMINI_KEY"))

def get_reply_bot():
    """تهيئة عميل X بصلاحية القراءة والكتابة (OAuth 1.0a)"""
    required_keys = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_SECRET"
    ]
    for key in required_keys:
        if not os.getenv(key):
            raise ValueError(f"❌ المتغير {key} غير مضبوط في GitHub Secrets.")

    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
        wait_on_rate_limit=True
    )

def is_valid_mention(tweet_text: str, bot_username: str) -> bool:
    """التحقق من أن التغريدة موجهة مباشرة للبوت"""
    return f"@{bot_username.lower()}" in tweet_text.lower()

def generate_smart_reply(question: str) -> str:
    """توليد رد ذكي باستخدام Gemini"""
    prompt = (
        "أنت بوت تقني ذكي ومهذب اسمك 'تيك بوت'.\n"
        "أجب عن السؤال التالي بإيجاز (لا تتجاوز جملتين)، بالعربية الفصحى، "
        "بأسلوب ودود ومحترف، ولا تكرر السؤال.\n\n"
        f"السؤال: {question}"
    )
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(contents=prompt)
        reply = response.text.strip()
        return reply[:270] + "..." if len(reply) > 280 else reply
    except Exception as e:
        logging.error(f"فشل توليد الرد: {e}")
        return "شكرًا لسؤالك! حاليًا أتعلم المزيد عن هذا الموضوع. 🤖✨"

def process_mentions(bot_username: str):
    client = get_reply_bot()

    # جلب معلومات الحساب (للتأكد من أن المصادقة صحيحة)
    try:
        user = client.get_me()
        user_id = user.data.id
        logging.info(f"تم الاتصال بحساب: @{user.data.username}")
    except Exception as e:
        logging.error(f"فشل المصادقة مع X API. تأكد من صحة المفاتيح الأربعة: {e}")
        return

    # جلب التغريدات الموجهة
    try:
        mentions = client.get_users_mentions(
            id=user_id,
            max_results=10,
            tweet_fields=["created_at", "author_id"]
        )
    except Exception as e:
        logging.error(f"فشل جلب التغريدات الموجهة: {e}")
        return

    if not mentions.
