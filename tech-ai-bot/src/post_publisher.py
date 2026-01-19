import os
import requests
import tweepy
import random
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import hashlib

# إعداد نظام التسجيل
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
            logging.info("تم اكتشاف محتوى مكرر — تم تجاهله.")
            return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

def generate_tech_content():
    """توليد محتوى تقني من OpenRouter — مع نص احتياطي عند الفشل."""
    try:
        # استخدم مفتاح OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY غير مضبوط.")

        # استخدم نموذج سريع وخفيف (مثلاً: llama-3.1-8b-instruct)
        model = "meta-llama/llama-3.1-8b-instruct"

        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }

        prompt = (
            "أجب عن السؤال التالي بإيجاز (لا تتجاوز جملتين)، بالعربية الفصحى، "
            "بأسلوب ودود ومحترف، ولا تكرر السؤال.\n\n"
            "السؤال: ما هو أحدث تطور في الذكاء الاصطناعي لعام 2026؟"
        )

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        return content, "https://openrouter.ai/"

    except Exception as e:
        logging.error(f"فشل توليد المحتوى من OpenRouter: {e}")
        # ✅ نص احتياطي
        fallback_content = [
            "اكتشف أحدث أدوات الذكاء الاصطناعي التي تغيّر عالمنا كل يوم 🤖",
            "هل تساءلت يومًا كيف يعمل الذكاء الاصطناعي؟ إليك نظرة سريعة! 🧠",
            "ابقَ على اطلاع دائم بأحدث التقنيات المذهلة في عالم الذكاء الاصطناعي!",
            "الذكاء الاصطناعي لا يحل محل البشر، بل يعزز قدراتهم! 💡",
            "تتطور التكنولوجيا بسرعة، ابقَ معها دائمًا! 🚀"
        ]
        return random.choice(fallback_content), "https://example.com/fallback"

def publish_tech_tweet():
    """نشر تغريدة تقنية على X."""
    logging.info("🚀 بدء مهمة النشر التلقائي...")
    try:
        content, url = generate_tech_content()

        if is_duplicate(content):
            return

        # ✅ استخدام المفاتيح الأربعة للنشر (OAuth 1.0a)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # بناء التغريدة
        max_text_len = 280 - len(url) - 10
        tweet_text = f"🛡️ موثوق | {content[:max_text_len]}\n\n🔗 {url}"

        if len(tweet_text) > 280:
            tweet_text = tweet_text[:275] + "..."

        # ✅ النشر الفعلي
        response = client.create_tweet(text=tweet_text)

        if response and response.
            tweet_id = response.data["id"]
            logging.info(f"✅ تم النشر بنجاح! رقم التغريدة: {tweet_id}")
        else:
            logging.warning("⚠️ لم يتم تأكيد النشر من X.")

    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
