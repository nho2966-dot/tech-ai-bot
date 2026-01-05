import os
import requests
import tweepy
import random
import google.genai as genai
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import hashlib
from datetime import datetime

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# تهيئة Gemini API
genai.configure(api_key=os.getenv("GEMINI_KEY"))

# ملف لتجنب النشر المتكرر
LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
            last_hash = f.read().strip()
        if current_hash == last_hash:
            logging.info("تم اكتشاف محتوى مكرر — تم تخطيه.")
            return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_tech_content():
    """جلب محتوى تقني موثوق من Tavily وتلخيصه عبر Gemini."""
    try:
        tavily_key = os.getenv("TAVILY_KEY")
        if not tavily_key:
            raise ValueError("TAVILY_KEY غير مضبوط في المتغيرات.")

        # طلب البحث من Tavily
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": "latest verified AI productivity tools and smartphone hacks 2026",
                "max_results": 3,
                "search_depth": "basic"
            },
            timeout=10
        )
        response.raise_for_status()
        search_res = response.json()

        if not search_res.get("results"):
            raise Exception("لم يتم العثور على نتائج من Tavily API.")

        # اختيار نتيجة عشوائية
        news = random.choice(search_res["results"])
        content_text = news.get("content") or news.get("snippet", "")
        source_url = news.get("url", "N/A")

        logging.info(f"تم جلب المحتوى من: {source_url}")

        # توليد الرد بالعربية عبر Gemini
        prompt = f"لخّص المحتوى التالي في جملة واحدة بالعربية الفصحى، بطريقة جذابة ومهنية، مناسبة لتغريدة تقنية: {content_text}"
        model = genai.GenerativeModel("gemini-2.0-flash")
        gemini_response = model.generate_content(contents=prompt)
        final_content = gemini_response.text.strip()

        if not final_content:
            raise Exception("Gemini أعاد محتوى فارغًا.")

        return final_content, source_url

    except Exception as e:
        logging.error(f"فشل جلب أو معالجة المحتوى: {e}")
        raise

def publish_tech_tweet():
    """نشر تغريدة تقنية على X."""
    logging.info("🚀 بدء مهمة النشر التلقائي...")
    try:
        content, source_url = generate_tech_content()

        if is_duplicate(content):
            return

        # تهيئة عميل X
        client = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN"))

        # بناء التغريدة
        max_content_len = 280 - len(source_url) - 10  # احتفظ بمساحة للرابط والرموز
        tweet_text = f"🛡️ موثوق | {content[:max_content_len]}\n\n🔗 {source_url}"

        if len(tweet_text) > 280:
            tweet_text = tweet_text[:275] + "..."

        # النشر الفعلي
        response = client.create_tweet(text=tweet_text)

        if response.data:
            tweet_id = response.data["id"]
            logging.info(f"✅ تم النشر بنجاح! رقم التغريدة: {tweet_id}")
        else:
            logging.warning("⚠️ لم يتم تأكيد النشر من X.")

    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
