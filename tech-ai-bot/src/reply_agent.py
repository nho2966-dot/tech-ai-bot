import os
import requests
import tweepy
import random
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed

# 1. إعداد المحرك (Gemini 2.0 Flash)
genai.configure(api_key=os.getenv('GEMINI_KEY'))

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_tech_content():
    # البحث عن أخبار تقنية موثوقة
    search_res = requests.post("https://api.tavily.com/search", json={
        "api_key": os.getenv('TAVILY_KEY'),
        "query": "newest verified AI tools and smartphone hacks Jan 2026",
        "max_results": 3
    }).json()
    
    news = random.choice(search_res['results'])
    
    # التوليد باستخدام الإصدار الأحدث
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"Summarize this for a tech tip in Arabic: {news['content']}. Ensure it's verified."
    response = model.generate_content(prompt)
    
    return response.text, news['url']

def run_mission():
    print("🚀 بدء محاولة النشر النهائية...")
    try:
        # جلب المحتوى
        content, source_url = generate_tech_content()

        # 2. إعداد عميل X (Twitter) بجميع الصلاحيات
        # تأكد أن هذه المفاتيح صحيحة في GitHub Secrets
        client = tweepy.Client(
            bearer_token=os.getenv('X_BEARER_TOKEN'),
            consumer_key=os.getenv('X_API_KEY'),
            consumer_secret=os.getenv('X_API_SECRET'),
            access_token=os.getenv('X_ACCESS_TOKEN'),
            access_token_secret=os.getenv('X_ACCESS_SECRET')
        )
        
        tweet_text = f"🛡️ موثوق | {content[:200]}\n\n🔗 {source_url}"
        
        # محاولة النشر الفعلية
        response = client.create_tweet(text=tweet_text)
        
        if response.data:
            print(f"✅ تم النشر بنجاح! رقم التغريدة: {response.data['id']}")
        else:
            print("⚠️ اكتمل السكريبت ولكن لم يتم تأكيد النشر من X.")

    except Exception as e:
        print(f"❌ خطأ تقني دقيق: {e}")

if __name__ == "__main__":
    run_mission()
