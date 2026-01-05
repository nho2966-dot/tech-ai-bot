import os
import requests
import tweepy
import random
from google import genai # التحديث للمكتبة الجديدة
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
    """جلب وتحليل محتوى تقني عبر Tavily، ثم تلخيصه عبر Gemini 2.0."""
    try:
        tavily_key = os.getenv("TAVILY_KEY")
        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY")) # الطريقة الجديدة

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": "أحدث أدوات الذكاء الاصطناعي وتقنيات الهواتف 2026",
                "max_results": 3,
                "search_depth": "basic"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            raise Exception("لا توجد نتائج من Tavily.")

        item = random.choice(data["results"])
        raw_content = item.get("content") or item.get("snippet", "")
        source_url = item.get("url", "N/A")

        prompt = (
            "لخّص المعلومة التقنية التالية في جملة واحدة مشوقة بالعربية الفصحى "
            "لتكون تغريدة احترافية. ابدأ بعبارة مثيرة ولا تكرر المحتوى: "
            f"{raw_content}"
        )

        # الاستدعاء الصحيح للموديل الجديد
        gemini_response = client_ai.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        summary = gemini_response.text.strip()

        return summary, source_url

    except Exception as e:
        logging.error(f"فشل في توليد المحتوى: {e}")
        raise

def publish_tech_tweet():
    """نشر التغريدة التقنية على X."""
    logging.info("🚀 بدء مهمة النشر التلقائي...")
    try:
        content, url = generate_tech_content()

        if is_duplicate(content):
            return

        # توحيد أسماء المتغيرات مع GitHub Secrets
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
            wait_on_rate_limit=True
        )

        tweet_text = f"⚙️ تقنية | {content}\n\nتفاصيل: {url}\n\n#تيك_بوت #AI"

        if len(tweet_text) > 280:
            tweet_text = tweet_text[:275] + "..."

        response = client.create_tweet(text=tweet_text)

        if response and response.data:
            logging.info(f"✅ تم النشر بنجاح! ID: {response.data['id']}")
        else:
            logging.warning("⚠️ لم يتم تأكيد النشر.")

    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
