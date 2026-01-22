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

# 1. إعداد الاتصال (X Premium Access)
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

# 2. محرك الذكاء الاصطناعي (OpenRouter - 2026 Model)
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

# 3. توليد السبق الصحفي (Exclusive Scoop)
def generate_exclusive_scoop():
    scoops = [
        "تسريبات حصرية: معالج Snapdragon 8 Gen 5 سيعتمد دقة 2nm لأول مرة في تاريخ الهواتف.",
        "خاص: أبل تختبر نظام تبريد سائل ثوري لـ iPhone 17 Pro لمواجهة متطلبات الذكاء الاصطناعي.",
        "تقرير: سوني تعمل على جهاز PlayStation Handheld يدعم تشغيل ألعاب PS5 سحابياً بـ 0 تأخير.",
        "براءة اختراع: سامسونج تطور شاشات قابلة للتمدد (Stretchable) ستغير مفهوم الأجهزة اللوحية.",
        "ثورة 2026: أول بطارية تعمل بتقنية الاندماج الكمي الصغير بدأت مرحلة الاختبار في اليابان."
    ]
    topic = random.choice(scoops)
    prompt = (
        f"أنت مراسل تقني عالمي لعام 2026. اكتب مقالاً لـ X Premium عن: {topic}.\n"
        "القواعد: ابدأ بـ [خاص وحصري]، استخدم لغة أرقام صادمة، أسلوب فصيح شبابي، رابط مصدر عالمي، وسؤال تفاعلي.\n"
        "#سبق_تقني #عُمان #Tech2026 #حصري"
    )
    return fetch_ai_response(prompt)

# 4. نظام الردود الذكية (Engagement)
def handle_mentions():
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        if not mentions.data: return

        for tweet in mentions.data:
            logging.info(f"💬 جاري الرد على: {tweet.id}")
            reply_prompt = f"رد بذكاء وفصاحة وإثارة على هذا التعليق التقني: {tweet.text}."
            reply_text = fetch_ai_response(reply_prompt, temp=0.7)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
    except Exception as e:
        logging.info(f"ℹ️ نظام الردود: {e}")

# 5. محرك النشر الرئيسي (وسائط + نص)
def publish_content():
    content = generate_exclusive_scoop()
    if not content: return
    try:
        img_url = "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1000"
        img_res = requests.get(img_url)
        with open('scoop.jpg', 'wb') as f: f.write(img_res.content)
        media = api_v1.media_upload(filename='scoop.jpg')
        client.create_tweet(text=content, media_ids=[media.media_id])
        logging.info("🔥 تم نشر السبق بنجاح!")
        os.remove('scoop.jpg')
    except Exception as e:
        logging.error(f"❌ فشل الوسائط: {e}")
        client.create_tweet(text=content)

# 6. التشغيل الذكي
def run_bot():
    try:
        me = client.get_me()
        if me.data:
            logging.info(f"✅ متصل كـ: @{me.data.username}")
            handle_mentions() # يحدث كل ساعة

            oman_tz = pyt
