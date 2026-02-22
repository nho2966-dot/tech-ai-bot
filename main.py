import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
import openai
from loguru import logger
import tweepy
from telegram import Bot

# تحميل متغيرات البيئة
load_dotenv()

# --- إعدادات اللوق ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger.info("Initializing Tech AI Bot...")

# --- إعداد مفاتيح OpenAI و Google GenAI ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_KEY = os.getenv("GEMINI_KEY")

openai.api_key = OPENAI_KEY
genai.configure(api_key=GOOGLE_KEY)

# --- إعداد حسابات التواصل ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
telegram_bot = Bot(token=TELEGRAM_TOKEN)

TWEEPY_API_KEY = os.getenv("TWEEPY_API_KEY")
TWEEPY_API_SECRET = os.getenv("TWEEPY_API_SECRET")
TWEEPY_ACCESS_TOKEN = os.getenv("TWEEPY_ACCESS_TOKEN")
TWEEPY_ACCESS_SECRET = os.getenv("TWEEPY_ACCESS_SECRET")

auth = tweepy.OAuth1UserHandler(
    TWEEPY_API_KEY, TWEEPY_API_SECRET, TWEEPY_ACCESS_TOKEN, TWEEPY_ACCESS_SECRET
)
twitter_api = tweepy.API(auth)

# --- دالة اختبار بسيطة ---
def test_ai_engines():
    try:
        # اختبار Google GenAI
        response_g = genai.Text.generate(model="chat-bison-001", prompt="Hello world!")
        logger.info(f"Google GenAI response: {response_g.text[:50]}...")

        # اختبار OpenAI
        response_o = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello world!"}]
        )
        logger.info(f"OpenAI response: {response_o.choices[0].message.content[:50]}...")

    except Exception as e:
        logger.error(f"AI test failed: {e}")

# --- تشغيل الاختبارات ---
if __name__ == "__main__":
    test_ai_engines()
    logger.info("Bot initialized successfully!")
