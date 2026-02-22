# main.py - نسخة مصححة للاستخدام مع GitHub Actions

import os
import logging
from datetime import datetime
import random
import sqlite3

# ✅ استيراد الحزم الصحيحة
import google.genai as genai  # بدل google.generativeai
import openai
import tweepy
import requests
from dotenv import load_dotenv
from python_telegram_bot import Bot  # إذا كنت تستخدم بوت تيليجرام

# إعداد البيئة والمتغيرات السرية
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_GENAI_KEY = os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# تهيئة السجلات
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- تهيئة الـ APIs ---
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GOOGLE_GENAI_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# --- قاعدة بيانات SQLite بسيطة ---
DB_FILE = "bot_data.db"
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT,
    created_at TEXT
)
""")
conn.commit()

# --- دوال مساعدة ---
def log_post(content):
    cursor.execute("INSERT INTO posts (content, created_at) VALUES (?, ?)", (content, datetime.utcnow()))
    conn.commit()
    logging.info(f"تم حفظ المنشور: {content[:50]}...")

def generate_content(prompt: str) -> str:
    """مثال على استخدام Google GenAI و OpenAI بالتتابع مع fallback"""
    try:
        response = genai.chat.create(model="chat-bison-001", messages=[{"role": "user", "content": prompt}])
        return response.last
    except Exception as e:
        logging.warning(f"GenAI failed, fallback to OpenAI: {e}")
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response['choices'][0]['message']['content']
        except Exception as e2:
            logging.error(f"OpenAI also failed: {e2}")
            return "حدث خطأ في توليد المحتوى."

# --- مثال تشغيل البوت ---
if __name__ == "__main__":
    logging.info("بدء تشغيل البوت")
    
    prompt = "اكتب تغريدة تقنية قصيرة ومبتكرة عن الذكاء الاصطناعي"
    content = generate_content(prompt)
    log_post(content)
    
    # إرسال المنشور على تيليجرام كمثال
    try:
        bot.send_message(chat_id="@YourChannelUsername", text=content)
        logging.info("تم إرسال المنشور على تيليجرام بنجاح")
    except Exception as e:
        logging.error(f"فشل إرسال المنشور على تيليجرام: {e}")

    logging.info("انتهاء التشغيل")
