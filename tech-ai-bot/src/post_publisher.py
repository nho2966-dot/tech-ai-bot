import os
import requests
import tweepy
import random
import google.genai as genai
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

# تهيئة مفتاح Gemini من المتغيرات السرية
genai.configure(api_key=os.getenv("GEMINI_KEY"))

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

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_tech_content():
    """جلب وتحليل محتوى تقني موثوق من Tavily، ثم تلخيصه عبر Gemini."""
    try:
        tavily_key = os.getenv("TAVILY_KEY")
        if not tavily_key:
            raise ValueError("TAVILY_KEY غير مضبوط في المتغيرات السرية.")

        # طلب البحث من Tavily API
        response = requests.post(
            "https://api.tavily.com/search",  # ✅ تم إصلاح المسافات
            json={
                "api_key": tavily_key,
                "query": "newest verified AI tools and smartphone hacks Jan 2026",
                "max_results": 3,
                "search_depth": "basic"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            raise Exception("لا توجد نتائج من Tavily API.")

        # اختيار نتيجة عشوائية
        item = random.choice(data["results"])
        raw_content = item.get("content") or item.get("snippet", "")
        source_url = item.get("url", "N/A")

        logging.info(f"تم جلب محتوى من: {source_url}")

        # توليد تلخيص جذاب بالعربية
        prompt = (
            "لخّص المحتوى التالي في جملة واحدة بالعربية الفصحى، "
            "بطريقة جذابة ومهنية، مناسبة لتغريدة تقنية قصيرة: "
            f"{raw_content}"
        )
        model = genai.GenerativeModel("gemini-2.0-flash")
        gemini_response = model.generate_content(contents=prompt)
        summary = gemini_response.text.strip()

        if not summary:
            raise Exception("Gemini أعاد محتوى فارغًا.")

        return summary, source_url

    except Exception as e:
        logging.error(f"فشل جلب أو توليد المحتوى: {e}")
        raise

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
        max_text_len = 280 - len(url) - 10  # مساحة للرابط والتنسيق
        import random
        tweet_text = f"🛡️ موثوق | {content[:max_text_len]}\n\n🔗 {url}\n\n#{random.randint(1000, 9999)}"

        if len(tweet_text) > 280:
            tweet_text = tweet_text[:275] + "..."

        # النشر الفعلي
        response = client.create_tweet(text=tweet_text)

        if response and response.data:
            tweet_id = response.data["id"]
            logging.info(f"✅ تم النشر بنجاح! رقم التغريدة: {tweet_id}")
        else:
            logging.warning("⚠️ لم يتم تأكيد النشر من X.")

    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
