# src/reply_agent.py

import os
import tweepy
import google.genai as genai  # ✅ تم الإصلاح: google.genai بدلاً من google.generativeai
from datetime import datetime, timezone
import logging
import hashlib

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# إعداد Gemini API
genai.configure(api_key=os.getenv('GEMINI_KEY'))

LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content):
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r") as f:
            last_hash = f.read().strip()
        if current_hash == last_hash:
            logging.info(f"Duplicate content detected with hash: {current_hash}")
            return True
    with open(LAST_HASH_FILE, "w") as f:
        f.write(current_hash)
    return False

def get_reply_bot():
    """إرجاع عميل X باستخدام Bearer Token"""
    return tweepy.Client(bearer_token=os.getenv('X_BEARER_TOKEN'))

def is_valid_mention(tweet_text, bot_username):
    """تحقق من أن التغريدة موجهة للبوت مباشرة"""
    return f"@{bot_username.lower()}" in tweet_text.lower()

def generate_smart_reply(question: str) -> str:
    """استخدم Gemini لإنشاء رد احترافي"""
    prompt = (
        "أنت بوت تقني ذكي ومهذب اسمك 'تيك بوت'.\n"
        "أجب عن السؤال التالي بإيجاز (لا تتجاوز جملتين)، بالعربية الفصحى، "
        "بأسلوب ودود ومحترف، ولا تكرر السؤال.\n\n"
        f"السؤال: {question}"
    )
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(contents=prompt)  # ✅ تم الإصلاح: contents=
        reply = response.text.strip()
        return reply[:270] + "..." if len(reply) > 280 else reply
    except Exception as e:
        logging.error(f"فشل توليد الرد: {e}")
        return "شكرًا لسؤالك! حاليًا أتعلم المزيد عن هذا الموضوع. 🤖✨"

def process_mentions(bot_username: str):
    client = get_reply_bot()
    
    try:
        user = client.get_me()
        user_id = user.data.id
    except Exception as e:
        logging.error(f"فشل جلب معلومات الحساب: {e}")
        return

    try:
        mentions = client.get_users_mentions(
            id=user_id,
            max_results=10,
            tweet_fields=["created_at", "author_id"]
        )
    except Exception as e:
        logging.error(f"فشل جلب التغريدات الموجهة: {e}")
        return

    if not mentions.data:
        logging.info("لا توجد تغريدات موجهة جديدة.")
        return

    for mention in mentions.data:
        created_at = mention.created_at
        if (datetime.now(timezone.utc) - created_at).total_seconds() > 3600:
            continue

        tweet_text = mention.text
        logging.info(f"معالجة تغريدة: {tweet_text}")

        if not is_valid_mention(tweet_text, bot_username):
            continue

        question = tweet_text.replace(f"@{bot_username}", "").strip()

        reply_text = generate_smart_reply(question)

        try:
            client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=mention.id
            )
            logging.info(f"تم الرد على التغريدة {mention.id}")
        except Exception as e:
            logging.error(f"فشل نشر الرد: {e}")

if __name__ == "__main__":
    BOT_USERNAME = os.getenv("BOT_USERNAME", "TechAI_Bot")
    process_mentions(BOT_USERNAME)
