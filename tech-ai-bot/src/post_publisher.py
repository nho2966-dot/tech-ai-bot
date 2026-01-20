import os
import requests
import tweepy
import random
import google.genai as genai
import logging
import hashlib

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
            last_hash = f.read().strip()
        if current_hash == last_hash:
            logging.info("تم اكتشاف محتوى مكرر.")
            return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

def generate_content_from_gemini():
    try:
        # استخدام المكتبة الجديدة المتوافقة مع 2.0 Flash
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        prompt = "أجب عن السؤال التالي بإيجاز (لا تتجاوز جملتين)، بالعربية الفصحى، بأسلوب محترف: ما هو أحدث تطور في الذكاء الاصطناعي لعام 2026؟"
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip(), "https://gemini.google.com/"
    except Exception as e:
        logging.error(f"فشل Gemini: {e}")
        return None, None

def generate_tech_content():
    content, source = generate_content_from_gemini()
    if content: return content, source

    # نص احتياطي في حال فشل الـ AI
    fallback_content = [
        "الذكاء الاصطناعي في 2026 يركز على الكفاءة والخصوصية بشكل أكبر 🛡️",
        "تطور النماذج الصغيرة SLMs هو الصيحة الحالية في عالم التقنية 🚀",
        "الاستدامة الرقمية أصبحت جزءاً لا يتجزأ من استراتيجيات الشركات التقنية 🔋"
    ]
    return random.choice(fallback_content), "https://tech-ai.bot"

def publish_tech_tweet():
    logging.info("🚀 بدء مهمة النشر التلقائي...")
    try:
        content, url = generate_tech_content()
        if is_duplicate(content): return

        # المصادقة بالمفاتيح الأربعة حصراً
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        tweet_text = f"🛡️ مـوثـوق | {content}\n\n🔗 {url}"
        
        # النشر
        response = client.create_tweet(text=tweet_text[:280])
        if response.data:
            logging.info(f"✅ تم النشر بنجاح! ID: {response.data['id']}")

    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
