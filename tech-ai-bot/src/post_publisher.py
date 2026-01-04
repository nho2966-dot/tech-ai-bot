# src/post_publisher.py
import os
import google.generativeai as genai
import requests
import tweepy
import random
import re
import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential

genai.configure(api_key=os.getenv('GEMINI_KEY'))

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

def clean_arabic_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s\d\-\.\،\!\؟\:\;\(\)\"\'\n]', '', text)
    return text.strip()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_tavily_data():
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": os.getenv('TAVILY_KEY'),
            "query": "verified latest AI tools and smartphone hacks 2025",
            "max_results": 3
        },
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def generate_summary(news_content):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (
            "أنت خبير تقني موثوق. قم بما يلي:\n"
            "1. لخّص المعلومة التالية بدقة باللغة العربية الفصحى.\n"
            "2. أضف نصيحة تقنية قصيرة وعملية (Tech Tip) مرتبطة بالمحتوى.\n"
            "3. تجنب الإطالة، وكن واضحًا ومباشرًا.\n"
            "4. لا تضيف روابط أو إشارات.\n\n"
            f"المحتوى: {news_content}"
        )
        response = model.generate_content(prompt, safety_settings={
            "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
        })
        content = response.text.strip() if response.text else ""
    except Exception as e1:
        print(f"⚠️ فشل Gemini 2.0: {e1}. التبديل إلى 1.5-flash...")
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"Summarize in Arabic: {news_content}")
            content = response.text.strip() if response.text else ""
        except Exception as e2:
            raise Exception(f"فشل كلا النموذجين: {e2}")

    if not content:
        raise Exception("لم يتم إنشاء أي محتوى من Gemini.")
    return content

def publish_tech_tweet():
    try:
        search_res = fetch_tavily_data()

        if not search_res.get('results'):
            raise Exception("لم يتم العثور على نتائج من Tavily API.")

        news = random.choice(search_res['results'])
        news_content = news.get('content') or news.get('snippet', '')
        if not news_content.strip():
            raise Exception("المحتوى فارغ من مصدر Tavily.")

        content = generate_summary(news_content)
        content = clean_arabic_text(content)

        if is_duplicate(content):
            print("✅ تم تجاهل التغريدة (مكررة).")
            return

        url = news['url']
        prefix = "🛡️ موثوق | "
        suffix = f"\n\n🔗 {url}"
        max_content_len = 280 - len(prefix) - len(suffix)

        if len(content) > max_content_len:
            content = content[:max_content_len - 3] + "..."

        tweet_text = prefix + content + suffix

       client = tweepy.Client(bearer_token=os.getenv('X_BEARER_TOKEN'))
        client.create_tweet(text=tweet_text)
        print("✅ تم النشر بنجاح!")

    except Exception as e:

        print(f"❌ خطأ فني: {e}")
