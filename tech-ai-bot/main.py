import os
import tweepy
import google.genai as genai
import requests
import logging
import hashlib
import random
from datetime import datetime, timezone
from dotenv import load_dotenv

# 1. إعدادات النظام والبيئة
load_dotenv()
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

LAST_HASH_FILE = "last_hash.txt"

# 2. وظائف منع التكرار والدقة
def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
            if f.read().strip() == current_hash:
                logging.info("🚫 محتوى مكرر تم رصده — إلغاء العملية.")
                return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

# 3. محركات توليد المحتوى (الموثوقية أولاً)
def generate_content():
    """توليد محتوى يعتمد على مصادر عالمية موثوقة."""
    
    trusted_sources = [
        "The Verge", "TechCrunch", "GSMArena", "Wired", "Reuters Technology", 
        "Bloomberg Tech", "9to5Mac", "Android Central", "Digital Trends"
    ]
    source = random.choice(trusted_sources)

    prompt = f"""
    أنت خبير تقني عالمي. اكتب تغريدة احترافية جداً بالعربية الفصحى بناءً على تقنيات حقيقية موثقة في ({source}).
    
    الهيكل المطلوب حرفياً:
    🛡️ التقنية: (اسم التقنية بالإنجليزية والعربية)
    💡 الأهمية: (شرح الفائدة بلغة الأرقام والمواصفات بدقة 100%)
    🛠️ التوظيف: (نصيحة عملية للمستخدم أو المطور)
    🌍 المصدر: [{source}]

    شروط صارمة:
    - ممنوع اختراع معلومات أو أسماء تقنيات وهمية.
    - استخدم لغة الأرقام والمقارنات (مثل السرعة، الطاقة، الأداء).
    - التغريدة يجب أن تكون أقل من 280 حرفاً.
    - ممنوع استخدام لغات غير العربية باستثناء المصطلحات التقنية.
    """

    # المحاولة الأولى: كوين (موديل 70B لضمان جودة المصادر)
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-70b-instruct",
            "messages": [
                {"role": "system", "content": "أنت محرر تقني في وكالة أنباء عالمية، تلتزم بالحقائق والمصادر الموثوقة فقط."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3 # درجة منخفضة جداً لضمان عدم التأليف
        }
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.warning(f"⚠️ تعذر كوين، محاولة جمناي: {e}")
        
    # المحاولة الثانية: جمناي كبديل
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"❌ فشلت جميع محركات التوليد: {e}")
        return None

# 4. وظيفة النشر على X
def publish_tweet():
    logging.info("🚀 بدء مهمة النشر الموثق...")
    
    content = generate_content()
    if not content or is_duplicate(content):
        return

    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # التأكد من طول النص
        final_text = content[:280]
        client.create_tweet(text=final_text)
        logging.info("✅ تم النشر بنجاح!")
    except Exception as e:
        logging.error(f"❌ فشل النشر على X: {e}")

if __name__ == "__main__":
    publish_tweet()
