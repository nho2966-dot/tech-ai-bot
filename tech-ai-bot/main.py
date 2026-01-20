import os
import tweepy
import google.genai as genai
import requests
import logging
import hashlib
import random
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# إعداد التسجيل (Logs)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ملف منع التكرار
LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
            if f.read().strip() == current_hash:
                logging.info("🚫 محتوى مكرر — تم التجاهل.")
                return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

def get_client():
    """تهيئة عميل X (التوافق مع الحساب المجاني)."""
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
        wait_on_rate_limit=False # لا نريد الانتظار الطويل في الأكشن
    )

def generate_tech_content():
    """توليد محتوى احترافي (نمط LTPO) مع نظام fallback."""
    prompt = (
        "اكتب تغريدة تقنية احترافية (نمط LTPO) بالعربية.\n"
        "1. التقنية\n2. الأهمية\n3. التوظيف\n4. المصدر."
    )
    
    # 1. محاولة جمناي
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip(), "https://gemini.google.com/"
    except Exception as e:
        logging.warning(f"⚠️ فشل جمناي: {e}. الانتقال لكوين...")

    # 2. محاولة كوين (OpenRouter)
    try:
        headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
        return res.json()["choices"][0]["message"]["content"].strip(), "https://openrouter.ai/"
    except Exception as e:
        logging.error(f"❌ فشل كوين أيضاً: {e}")
        return "الذكاء الاصطناعي يتطور لخدمة البشرية بشكل أسرع كل يوم. 🚀", "https://techbot.ai"

def publish_tech_tweet():
    logging.info("🚀 بدء مهمة النشر...")
    try:
        content, source_url = generate_tech_content()
        if is_duplicate(content): return

        client = get_client()
        # تنسيق التغريدة لتناسب 280 حرفاً
        tweet_text = f"🛡️ موثوق | {content[:200]}\n\n🔗 {source_url}"
        client.create_tweet(text=tweet_text)
        logging.info("✅ تم النشر بنجاح!")
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

def main():
    bot_username = os.getenv("BOT_USERNAME", "X_TechNews_")
    logging.info(f"🤖 تشغيل البوت للحساب: @{bot_username}")
    
    # في GitHub Actions نشغل المهمة مرة واحدة عند كل استدعاء
    publish_tech_tweet()
    # يمكنك إضافة استدعاء الردود هنا إذا كانت الصلاحيات تسمح (Read/Write)
    # process_mentions(bot_username)

if __name__ == "__main__":
    main()
