import os
import tweepy
import requests
import logging
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv

# إعدادات التسجيل والـوُضُـوح
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

# 1. إعداد الاتصال بـ X (Premium Access)
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

# 2. محرك الذكاء الاصطناعي (OpenRouter)
def fetch_ai_response(prompt, temp=0.9):
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temp
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ AI: {e}")
        return None

# 3. توليد السبق الصحفي (ديناميكي حسب السنة)
def generate_exclusive_scoop():
    oman_tz = pytz.timezone('Asia/Muscat')
    current_year = datetime.now(oman_tz).year
    
    prompt = (
        f"أنت مراسل تقني رائد في عام {current_year}. اكتب سبقاً صحفياً لـ X Premium.\n"
        "المحتوى: تسريبات حصرية، أرقام تقنية صادمة، أو ثورة في عالم الذكاء الاصطناعي.\n"
        "القواعد: ابدأ بـ [خاص وحصري]، لغة فصيحة، رابط مصدر عالمي، سؤال ناري.\n"
        f"الوسوم: #{current_year} #سبق_تقني #عُمان"
    )
    return fetch_ai_response(prompt)

# 4. نظام الردود (يعمل كل ساعة)
def handle_mentions():
    try:
        me = client.get_me()
        if not me.data: return
        
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        if not mentions.data:
            logging.info("ℹ️ لا توجد منشنز جديدة حالياً.")
            return

        for tweet in mentions.data:
            reply_text = fetch_ai_response(f"رد بذكاء وفصاحة على: {tweet.text}")
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد على التغريدة {tweet.id}")
    except Exception as e:
        logging.info(f"ℹ️ تنبيه في الردود (قد يكون 401 أو لا يوجد جديد): {e}")

# 5. محرك النشر (وسائط + نص)
def publish_content():
    content = generate_exclusive_scoop()
    if not content: return
    try:
        img_url = "
