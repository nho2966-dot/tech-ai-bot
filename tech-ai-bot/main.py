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

# 1. إعداد الاتصال بـ X
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

# 3. توليد السبق الصحفي (ديناميكي حسب السنة الحالية)
def generate_exclusive_scoop():
    oman_tz = pytz.timezone('Asia/Muscat')
    current_year = datetime.now(oman_tz).year
    next_year = current_year + 1

    prompt = (
        f"أنت مراسل تقني عالمي في عام {current_year}. اكتب سبقاً صحفياً لـ X Premium.\n"
        f"الموضوع: أخبار حصرية، تسريبات مصانع، أو تقنيات ثورية متوقعة في نهاية {current_year} وبداية {next_year}.\n"
        "القواعد:\n"
        "1. ابدأ بـ [خاص وحصري] مع إثارة قصوى.\n"
        "2. استخدم لغة الأرقام الصادمة والأسلوب الفصيح الشبابي.\n"
        "3. اذكر رابط مصدر تقني عالمي حقيقي.\n"
        f"4. استخدم وسم #{current_year} ووسوم تقنية عامة.\n"
        "5. اختم بسؤال تفاعلي للمتابعين."
    )
    return fetch_ai_response(prompt)

# 4. نظام الردود الذكية (كل ساعة)
def handle_mentions():
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        if not mentions.data: return

        for tweet in mentions.data:
            reply_prompt = f"رد بذكاء وفصاحة على هذا التعليق التقني: {tweet.text}. اجعل الرد مواكباً للتطورات التقنية الحالية."
            reply_text = fetch_ai_response(reply_prompt, temp=0.7)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد بنجاح.")
    except Exception as e:
        logging.info(f"ℹ️ تنبيه في الردود: {e}")

# 5. محرك النشر (وسائط + نص)
def publish_content():
    content = generate_exclusive_scoop()
    if not content: return
    try:
        img_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1000"
        img_res = requests.get(img_url)
        img_path = os.path.join(os.getcwd(), 'scoop_img.jpg')
        with open(img_path, 'wb') as f: f.write(img_res.content)

        media = api_v1.media_upload(filename=img_path)
        client.create_tweet(text=content, media_ids=[media.media_id])
        logging.info("🔥 تم نشر السبق الدوري!")
        if os.path.exists(img_path): os.remove(img_path)
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")
        client.create_tweet(text=content)

# 6. التشغيل الرئيسي (رد كل ساعة - نشر كل 6 ساعات)
if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    now = datetime.now(oman_tz)
    
    # الردود تعمل في كل دورة (كل ساعة)
    handle_mentions()

    # النشر الرئيسي يتم فقط في الساعات 0, 6, 12, 18 بتوقيت عُمان
    if now.hour % 6 == 0:
        publish_content()
