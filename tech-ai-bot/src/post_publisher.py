import os
import requests
import tweepy
import random
from google import genai
import logging
import hashlib
import time

# إعداد نظام التسجيل (تأكد من وجود مجلد logs أو سيتم العرض في الشاشة فقط)
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ملف منع التكرار
LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
            last_hash = f.read().strip()
        if current_hash == last_hash:
            logging.info("⚠️ تم اكتشاف محتوى مكرر — تم تجاهله.")
            return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

def generate_content_from_gemini():
    """توليد محتوى من Gemini 2.0 Flash."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            raise ValueError("GEMINI_KEY غير مضبوط.")
        
        client = genai.Client(api_key=api_key)
        prompt = "أعطني معلومة تقنية مذهلة وجديدة عن الذكاء الاصطناعي لعام 2026 لتغريدة عربية مشوقة (جملتين فقط) مع هاشتاقات."
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        
        if response and response.text:
            return response.text.strip(), "https://gemini.google.com/"
        return None, None
    except Exception as e:
        logging.error(f"❌ فشل توليد المحتوى من Gemini: {e}")
        return None, None

def generate_content_from_openrouter():
    """توليد محتوى من OpenRouter كخطة بديلة."""
    try:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            return None, None

        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "أعطني معلومة تقنية عن الذكاء الاصطناعي لعام 2026 باختصار شديد بالعربية."}],
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload, headers=headers, timeout=15
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip(), "https://openrouter.ai/"
    except Exception as e:
        logging.error(f"❌ فشل توليد المحتوى من OpenRouter: {e}")
        return None, None

def publish_tech_tweet():
    """المهمة الرئيسية: توليد ثم نشر التغريدة."""
    logging.info("🚀 بدء مهمة النشر التلقائي...")
    try:
        # 1. محاولة Gemini أولاً
        content, source = generate_content_from_gemini()
        
        # 2. إذا فشل Gemini، جرب OpenRouter
        if not content:
            logging.info("🔄 المحاولة عبر OpenRouter...")
            content, source = generate_content_from_openrouter()
            
        # 3. إذا فشل الكل، استخدم نص احتياطي
        if not content:
            logging.warning("⚠️ استخدام محتوى احتياطي.")
            fallbacks = [
                "الذكاء الاصطناعي في 2026 يتجاوز التوقعات، ترقبوا ثورة في معالجة البيانات اللحظية! 🚀 #تقنية",
                "مستقبل التقنية يبدأ اليوم؛ النماذج اللغوية أصبحت أكثر ذكاءً وقدرة على فهم السياق العربي. 🧠"
            ]
            content, source = random.choice(fallbacks), "https://tech-bot.ai"

        # منع التكرار
        if is_duplicate(content):
            return

        # 4. إعداد عميل X
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # بناء النص النهائي (بحد أقصى 280 حرف)
        final_tweet = f"{content[:250]}\n\n#AI2026 #ذكاء_اصطناعي"
        
        client.create_tweet(text=final_tweet)
        logging.info("✅ تم النشر بنجاح على منصة X!")

    except Exception as e:
        logging.error(f"❌ خطأ فادح في العملية: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
