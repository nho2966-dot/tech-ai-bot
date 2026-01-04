import os
import requests
import tweepy
import random
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import hashlib

# إعداد الصلاحيات
genai.configure(api_key=os.getenv('GEMINI_KEY'))

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content):
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r") as f:
            last_hash = f.read().strip()
        if current_hash == last_hash:
            return True
    with open(LAST_HASH_FILE, "w") as f:
        f.write(current_hash)
    return False

# نظام إعادة المحاولة لضمان الموثوقية (3 محاولات)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_tech_content():
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": os.getenv('TAVILY_KEY'),
                "query": "newest verified AI tools and smartphone hacks Jan 2026",
                "max_results": 3
            },
            timeout=10
        )
        response.raise_for_status()
        search_res = response.json()

        if not search_res.get('results'):
            raise Exception("No results from Tavily API.")

        news = random.choice(search_res['results'])
        content_text = news.get('content') or news.get('snippet', '')

        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"Summarize this for a tech tip in Arabic: {content_text}. Ensure it's verified."
        response = model.generate_content(prompt)
        
        content = response.text.strip()
        if not content:
            raise Exception("Gemini returned empty content.")

        return content, news['url']

    except Exception as e:
        raise Exception(f"Failed to fetch content: {e}")

def run_mission():
    logging.info("🚀 بدء محاولة النشر النهائية...")
    try:
        # 1. جلب المحتوى مع نظام إعادة المحاولة
        content, source_url = generate_tech_content()

        # 2. التحقق من التكرار
        if is_duplicate(content):
            logging.info("✅ تم تجاهل التغريدة (مكررة).")
            return

        # 3. إعداد عميل X (Twitter) بجميع الصلاحيات
        client = tweepy.Client(
            bearer_token=os.getenv('X_BEARER_TOKEN'),
            consumer_key=os.getenv('X_API_KEY'),
            consumer_secret=os.getenv('X_API_SECRET'),
            access_token=os.getenv('X_ACCESS_TOKEN'),
            access_token_secret=os.getenv('X_ACCESS_SECRET')
        )

        tweet_text = f"🛡️ موثوق | {content[:200]}\n\n🔗 {source_url}"

        # 4. محاولة النشر الفعلية
        response = client.create_tweet(text=tweet_text)

        if response.data:
            logging.info(f"✅ تم النشر بنجاح! رقم التغريدة: {response.data['id']}")
        else:
            logging.warning("⚠️ اكتمل السكريبت ولكن لم يتم تأكيد النشر من X.")

    except Exception as e:
        logging.error(f"❌ خطأ تقني دقيق: {e}")

if __name__ == "__main__":
    run_mission()
