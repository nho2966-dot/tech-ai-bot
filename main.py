# main.py
import os
import logging
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import google.generativeai as genai
import openai

# === إعداد السجلات ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# === مفاتيح API ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GENAI_API_KEY = os.getenv("GEMINI_KEY")

# === إعداد العملاء ===
bot = Bot(token=TELEGRAM_TOKEN)
genai.configure(api_key=GENAI_API_KEY)
openai.api_key = OPENAI_API_KEY

# === دالة إرسال رسالة على تيليجرام مع تسجيل الأخطاء ===
def send_telegram_message(chat_id: str, text: str):
    try:
        bot.send_message(chat_id=chat_id, text=text)
        logging.info(f"تم إرسال الرسالة بنجاح إلى {chat_id}")
    except TelegramError as e:
        logging.error(f"فشل إرسال الرسالة: {e}")

# === دالة معالجة النص باستخدام الذكاء الاصطناعي مع fallback ===
def ai_process(prompt: str) -> str:
    # محاولة GenAI أولاً
    try:
        logging.info("محاولة استخدام Google GenAI...")
        response = genai.generate_text(model="text-bison-001", prompt=prompt)
        return response.text
    except Exception as e:
        logging.error(f"GenAI فشل: {e}")

    # محاولة OpenAI كـ fallback
    try:
        logging.info("محاولة استخدام OpenAI...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI فشل: {e}")

    # في حالة فشل الكل
    logging.critical("فشل كل المزودين! العودة برسالة خطأ.")
    return "حدث خطأ ولم نتمكن من معالجة الطلب."

# === مثال استخدام ===
if __name__ == "__main__":
    chat_id = os.getenv("TEST_CHAT_ID")  # ضع هنا معرف القناة أو المستخدم
    prompt = "اكتب لي تغريدة تقنية قصيرة عن الذكاء الاصطناعي."
    ai_response = ai_process(prompt)
    send_telegram_message(chat_id, ai_response)
