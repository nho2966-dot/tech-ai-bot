import os
import tweepy
import google.genai as genai
import requests
import logging
import hashlib
import random
from datetime import datetime
from dotenv import load_dotenv

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

LAST_HASH_FILE = "last_hash.txt"

# 2. وظائف الحماية والتدقيق
def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    try:
        if os.path.exists(LAST_HASH_FILE):
            with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
                if f.read().strip() == current_hash:
                    logging.info("🚫 محتوى مكرر تم رصده — إلغاء النشر.")
                    return True
        with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
            f.write(current_hash)
        return False
    except Exception as e:
        logging.warning(f"⚠️ تنبيه في ملف الهاش: {e}")
        return False

# 3. محرك توليد المحتوى الاحترافي
def generate_tech_content():
    trusted_sources = [
        "The Verge", "TechCrunch", "GSMArena", "Wired", 
        "Reuters Tech", "Bloomberg Technology", "9to5Mac"
    ]
    source = random.choice(trusted_sources)

    # تم تصحيح إغلاق علامات الاقتباس هنا
    prompt = f"اكتب تغريدة تقنية احترافية جداً بالعربية الفصحى بناءً على أخبار موثوقة من ({source}). الهيكل: 🛡️ التقنية، 💡 الأهمية (بالأرقام)، 🛠️ التوظيف، 🌍 المصدر: [{source}]. الشروط: حقيقية، رصينة، وأقل من 260 حرفاً."

    # المحاولة الأولى: OpenRouter (Llama 3.1 70B)
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-70b-instruct",
            "messages": [
                {"role": "system", "content": "أنت محرر تقني عالمي يكتب حقائق موثقة فقط."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            logging.info(f"✅ تم التوليد عبر كوين (المصدر: {source})")
            return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.warning(f"⚠️ فشل كوين، محاولة جمناي: {e}")

    # المحاولة الثانية: Gemini
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        logging.info(f"✅ تم التوليد عبر جمناي")
        return response.text.strip()
    except Exception as e:
        logging.error(f"❌ فشل التوليد تماماً: {e}")
        return None

# 4. وظيفة النشر الأساسية
def publish_tweet():
    logging.info("🚀 بدء مهمة النشر الموثق...")
    content = generate_tech_content()
    if not content or is_duplicate(content):
        return

    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر بنجاح على منصة X!")
    except Exception as e:
        logging.error(f"❌ خطأ النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
