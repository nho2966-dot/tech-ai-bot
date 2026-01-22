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

# 3. توليد السبق الصحفي الرئيسي
def generate_exclusive_scoop():
    scoops = [
        "تسريبات من مختبرات أبل: نظارات Vision Air القادمة ستدعم الترجمة الفورية للهجات المحلية العربية.",
        "تقرير حصري: معالجات سامسونج 2026 ستستخدم تكنولوجيا 'الغرافين' لتقليل الحرارة بنسبة 50%.",
        "مشروع سري: إيلون ماسك يلمح لدمج Starlink مباشرة في هواتف X القادمة لإنهاء عصر أبراج الاتصال.",
        "خاص: تسريب مواصفات كاميرا Galaxy S26 Ultra - زووم بصري يصل لـ 200x بذكاء اصطناعي هجين."
    ]
    topic = random.choice(scoops)
    prompt = (
        f"اكتب سبقاً صحفياً لـ X Premium عن: {topic}.\n"
        "ابدأ بـ [خاص وحصري]، استخدم أرقاماً، لغة فصيحة شبابية، رابط مصدر، وسؤال ناري.\n"
        "#سبق_تقني #عُمان #Tech2026"
    )
    return fetch_ai_response(prompt)

# 4. نظام الردود الذكية (كل ساعة)
def handle_mentions():
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        if not mentions.data:
            logging.info("ℹ️ لا توجد تعليقات جديدة للرد عليها.")
            return

        for tweet in mentions.data:
            reply_prompt = f"رد بذكاء وفصاحة على هذا التعليق التقني: {tweet.text}"
            reply_text = fetch_ai_response(reply_prompt, temp=0.7)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد على {tweet.id}")
    except Exception as e:
        logging.info(f"ℹ️ تنبيه في الردود: {e}")

# 5. محرك النشر الرئيسي (كل 6 ساعات)
def publish_content():
    content = generate_exclusive_scoop()
    if not content: return
    try:
        # صورة تقنية عشوائية
        img_url = "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?q=80&w=1000"
        img_res = requests.get(img_url)
        img_path = os.path.join(os.getcwd(), 'scoop_img.jpg') # مسار ديناميكي
        with open(img_path, 'wb') as f: f.write(img_res.content)

        media = api_v1.media_upload(filename=img_path)
        client.create_tweet(text=content, media_ids=[media.media_id])
        logging.info("🔥 تم نشر السبق الصحفي بنجاح!")
        if os.path.exists(img_path): os.remove(img_path)
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")
        client.create_tweet(text=content)

# 6. التشغيل الرئيسي
if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    now = datetime.now(oman_tz)
    logging.info(f"🕒 الوقت الحالي في عُمان: {now.strftime('%H:%M')}")

    # الردود دائماً (كل ساعة)
    handle_mentions()

    # النشر الرئيسي (كل 6 ساعات: 0, 6, 12, 18)
    if now.hour % 6 == 0:
        publish_content()
    else:
        logging.info("ℹ️ الردود تمت، النشر الرئيسي في الدورة القادمة.")
