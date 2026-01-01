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
def get_verified_content():
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": os.getenv('TAVILY_KEY'),
                "query": "latest verified AI productivity tools and smartphone hacks 2026",
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
    logging.info("🚀 انطلاق المهمة بنظام الموثوقية العالي...")
    try:
        # 1. جلب المحتوى مع نظام إعادة المحاولة
       
