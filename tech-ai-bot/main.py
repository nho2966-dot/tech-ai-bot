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

# 1. إعداد الاتصال (V2 للنشر و V1.1 لرفع الوسائط)
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

# 2. دالة جلب المحتوى من الذكاء الاصطناعي (محرك يناير 2026)
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

# 3. محرك السبق الصحفي (Exclusive Scoop Generator)
def generate_exclusive_scoop():
    scoop_topics = [
        "تسريبات من مصانع TSMC عن قفزة بنسبة 40% في أداء معالجات 2nm القادمة.",
        "براءة اختراع مسربة لنظارات AR من أبل تعوض الهواتف تماماً بحلول 2027.",
        "مشروع سري بين OpenAI وسامسونج لتطوير رقائق ذكاء اصطناعي سيادي.",
        "تحليل بيانات سلاسل الإمداد: هل تخلت سوني عن منصات الكونسول لصالح السحاب؟",
        "تقرير حصري: ثغرة في أنظمة التشفير الكمي تهدد خصوصية البيانات العالمية."
    ]
    topic = random.choice(scoop_topics)
    
    prompt = (
        f"أنت مراسل تقني عالمي متخصص في السبق الصحفي لعام 2026. اكتب مقالاً لـ X Premium عن: {topic}.\n"
        "القواعد:\n"
        "1. ابدأ بـ [خاص وحصري] أو [تسريب عاجل] مع أرقام صادمة وإثارة كبرى.\n"
        "2. لغة الشباب: سريعة، فصيحة، ومختصرة (لا حشو).\n"
        "3. المصداقية: اذكر رابط مصدر تقني عالمي حقيقي (مثل bloomberg.com أو macrumors.com).\n"
        "4. التفاعل: اختم بسؤال 'ناري' يثير الجدل التقني.\n"
        "5. الطول: حوالي 800 حرف.\n"
        "#سبق_تقني #تسريبات #عُمان #AI2026 #حصري"
    )
    return fetch_ai_response(prompt)

# 4. نظام الردود الذكية (Engagement System)
def handle_mentions():
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        if not mentions.data: return

        for tweet in mentions.data:
            logging.info(f"💬 رد ذكي على: {tweet.id}")
            reply_prompt = f"رد بشكل فصيح ومثير للتشويق على هذا التعليق التقني: {tweet.text}"
            reply_text = fetch_ai_response(reply_prompt, temp=0.7)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
    except Exception as e:
        logging.info(f"ℹ️ نظام الردود: {e}")

# 5. محرك النشر المتكامل (الوسائط + النص + الرابط)
def publish_content():
    content = generate_exclusive_scoop()
    if not content: return

    try:
        # تحميل صورة تقنية عشوائية بجودة عالية تعبر عن 2026
        img_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1000"
        img_res = requests.get(img_url)
        with open('scoop_media.jpg', 'wb') as f:
            f.write(img_res.content)

        # رفع الوسائط
        media = api_v1.media_upload(filename='scoop_media.jpg')
        
        # النشر النهائي
        client.create_tweet(text=content, media_ids=[media.media_id])
        logging.info("🔥 تم نشر السبق الصحفي بنجاح مع الوسائط!")
        
        os.remove('scoop_media.jpg')
    except Exception as e:
        logging.error(f"❌ فشل النشر المتكامل: {e}")
        client.create_tweet(text=content) # خطة بديلة: نص فقط

# 6. التشغيل الرئيسي
if __name__ == "__main__":
    logging.info("🚀 انطلاق رادار التقنية - نسخة السبق الصحفي 2026...")
    try:
        # فحص الهوية
        identity = client.get_me()
        if identity.data:
            logging.info(f"✅ متصل كـ: @{identity.data.username}")
            handle_mentions() # تفاعل أولاً
            publish_content() # انشر السبق ثانياً
    except Exception as e:
        logging.error(f"⚠️ فشل في بدء العمل: {e}")
