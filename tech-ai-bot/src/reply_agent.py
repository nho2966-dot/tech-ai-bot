# src/reply_agent.py
import os
import tweepy
import google.generativeai as genai
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)

genai.configure(api_key=os.getenv('GEMINI_KEY'))

def get_reply_bot():
    return tweepy.Client(
        consumer_key=os.getenv('X_API_KEY'),
        consumer_secret=os.getenv('X_API_SECRET'),
        access_token=os.getenv('X_ACCESS_TOKEN'),
        access_token_secret=os.getenv('X_ACCESS_SECRET'),
        wait_on_rate_limit=True
    )

def is_valid_mention(tweet_text, @X_TechNews_):
    """تحقق من أن التغريدة موجهة للبوت مباشرة"""
    return f"@{X_TechNews_.lower()}" in tweet_text.lower()

def generate_smart_reply(question: str) -> str:
    """استخدم Gemini لإنشاء رد احترافي"""
    prompt = (
        "أنت بوت تقني ذكي ومهذب اسمك 'تيك بوت'.\n"
        "أجب عن السؤال التالي بإيجاز (لا تتجاوز جملتين)، بالعربية الفصحى، "
        "بأسلوب ودود ومحترف، ولا تكرر السؤال.\n\n"
        f"السؤال: {question}"
    )
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, safety_settings={
            "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
        })
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

