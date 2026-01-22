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

# 3. توليد السبق الصحفي (The Exclusive Scoop)
def generate_exclusive_scoop():
    scoops = [
        "تسريبات حصرية عن معالج Apple A20 القادم: قفزة تاريخية في كفاءة الطاقة بنسبة 35%.",
        "تقرير من سلاسل الإمداد: سامسونج تستعد لإطلاق أول هاتف 'شفاف' بالكامل في 2027.",
        "خاص: اكتشاف ميزة سرية في تحديث Grok 3 تسمح بالتحكم في الأجهزة المنزلية عبر التفكير.",
        "سقوط مبيعات الـ PC التقليدي: هل تسيطر نظارات الواقع المختلط على سوق العمل في عُمان؟",
        "ثورة البطاريات: تقنية 'النانو-سيليكون' ستجعل هاتفك يعمل لمدة أسبوع بشحنة واحدة."
    ]
    topic = random.choice(scoops)
    prompt = (
        f"أنت مراسل تقني عالمي متخصص في السبق الصحفي لعام 2026. اكتب مقالاً لـ X Premium عن: {topic}.\n"
        "الشروط: ابدأ بـ [خاص وحصري]، استخدم أرقاماً دقيقة، لغة فصيحة وشبابية، أضف رابط مصدر عالمي، واختم بسؤال تفاعلي ناري.\n"
        "#سبق_تقني #ترند_عُمان #AI2026 #حصري"
    )
    return fetch_ai_response(prompt)

# 4. نظام الردود الذكية (Engagement System)
def handle_mentions():
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        if not mentions.data:
            logging.info("ℹ️ لا توجد تعليقات جديدة للرد عليها حالياً.")
            return

        for tweet in mentions.data:
            logging.info(f"💬 جاري الرد على المتابع في التغريدة: {tweet.id}")
            reply_prompt = f"رد بذكاء وفصاحة وإثارة على هذا التعليق التقني: {tweet.text}. اجعل الرد قصيراً ومحفزاً."
            reply_text = fetch_ai_response(reply_prompt, temp=0.7)
            if reply_text:
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logging.info(f"✅ تم الرد بنجاح على {tweet.id}")
    except Exception as e:
        logging.info(f"ℹ️ تنبيه في نظام الردود: {e}")

# 5. محرك النشر (الوسائط + النص)
def publish_content():
    content = generate_exclusive_scoop()
    if not content: return
    try:
        # اختيار صورة تقنية مستقبلية
        img_url = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=1000"
        img_res = requests.get(img_url)
        with open('scoop.jpg', 'wb') as f: f.write(img_res.content)

        media = api_v1.media_upload(filename='scoop.jpg')
        client.create_tweet(text=content, media_ids=[media.media_id])
        logging.info("🔥 تم نشر السبق الصحفي الرئيسي بنجاح!")
        os.remove('scoop.jpg')
    except Exception as e:
        logging.error(f"❌ فشل نشر الوسائط: {e}")
        client.create_tweet(text=content)

# 6. التشغيل الذكي (رد كل ساعة - نشر كل 6 ساعات)
def run_bot():
    logging.info("🚀 بدء دورة العمل الذكية...")
    try:
        me = client.get_me()
        if me.data:
            logging.info(f"✅ متصل كـ: @{me.data.username}")
            
            # الرد دائماً (لأنه يعمل كل ساعة عبر GitHub)
            handle_mentions()

            # تحديد وقت النشر (كل 6 ساعات بتوقيت عُمان)
            oman_tz = pytz.timezone('Asia/Muscat')
            current_hour = datetime.now(oman_tz).hour
            
            if current_hour % 6 == 0:
                logging.info(f"⏰ حان موعد النشر الرئيسي (الساعة {current_hour})")
                publish_content()
            else:
                logging.info(f"ℹ️ ردود فقط. النشر القادم في الساعة القادمة التي تقبل القسمة على 6.")
    except Exception as e:
        logging.error(f"⚠️ خطأ في التشغيل: {e}")

if __name__ == "__main__":
    run_bot()
