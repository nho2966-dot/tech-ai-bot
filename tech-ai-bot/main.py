import os
import tweepy
import requests
import logging
import random
import re
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv

# ✅ إعدادات النخبة والـوُضُـوح
load_dotenv()
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [MASTER-AI] - %(message)s',
    handlers=[logging.FileHandler("agent.log", encoding='utf-8'), logging.StreamHandler()]
)

# ✅ تهيئة الوصول الموحد (V2 + Bearer) لضمان تجاوز أخطاء الصلاحيات
try:
    client = tweepy.Client(
        bearer_token=os.getenv("X_BEARER_TOKEN"),
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
        wait_on_rate_limit=True
    )
    logging.info("🔐 تم تفعيل بروتوكول الكاريزما والحوار المباشر بـوُضُـوح.")
except Exception as e:
    logging.error(f"❌ خطأ في الاتصال: {e}")

ARCHIVE_FILE = "published_archive.txt"

def is_duplicate(identifier):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return identifier.lower()[:60] in f.read().lower()

def save_to_archive(identifier):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {identifier}\n")

def generate_ai_content(prompt_type, context_data=""):
    try:
        # هندسة البرومبت: مزيج الود، الجدية، الحسم، والسؤال المباشر
        system_persona = (
            "أنت 'Cyber Hunter' - الخبير التقني ذو الكاريزما العالية. "
            "أسلوبك المعتمد بـوُضُـوح: "
            "1. الود: ابدأ دائماً بتحية دافئة ومخصصة للمتابع (مثال: أهلاً بك يا صديقي، حيّاك الله..). "
            "2. الجدية والحسم: قدم تحليلاً تقنياً عميقاً وحاسماً، استخدم مصطلحات مثل (المعمارية، النانومتر، التشفير السيادي). "
            "3. السؤال المباشر (إلزامي): يجب أن تنتهي كل إجابة بسؤال صريح ومباشر موجه للمتابع بصيغة (أنت)، "
            "على أن يكون السؤال مثيراً للجدل التقني ليدفعه للرد ومناقشتك بـوُضُـوح. "
            "4. التنسيق: استخدم الإيموجيات (🚀, 🧠, 🛡️) لزيادة الجاذبية البصرية."
        )
        
        if prompt_type == "reply":
            user_msg = f"رد بأسلوبك الكاريزمي على هذا المنشن واختم بسؤال مباشر وصريح جداً للمتابع: {context_data}"
        else:
            user_msg = f"اكتب تقريراً استراتيجياً حاسماً وانتهِ بسؤال مباشر يوجه للجمهور بـوُضُـوح حول: {context_data}"

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [
                    {"role": "system", "content": system_persona},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.6, 
                "max_tokens": 1000
            }, timeout=60
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ خطأ في توليد المحتوى: {e}")
        return None

def post_scoop():
    # مواضيع استراتيجية تثير النقاش
    topics = [
        "مستقبل الذكاء الاصطناعي وتجاوزه للقدرات البشرية",
        "حرب الرقائق الإلكترونية بين القوى العظمى",
        "تأثير الحوسبة الكمومية على أمن البيانات العالمي",
        "استبدال الهواتف الذكية بتقنيات النظارات المعززة"
    ]
    topic = random.choice(topics)
    content = generate_ai_content("post", topic)
    if not content: return
    
    try:
        client.create_tweet(text=content[:280])
        logging.info(f"🔥 تم نشر محتوى تفاعلي بـوُضُـوح.")
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

def auto_reply():
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(id=me.id, max_results=5)
        if not mentions or not mentions.data: 
            logging.info("🔎 لا توجد إشارات جديدة حالياً.")
            return

        for tweet in mentions.data:
            reply_id = f"reply_{tweet.id}"
            if is_duplicate(reply_id): continue
            
            reply_text = generate_ai_content("reply", tweet.text)
            if reply_text:
                client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                save_to_archive(reply_id)
                logging.info(f"💬 تم الرد المباشر والمثير للجدل على: {tweet.id}")
    except Exception as e:
        logging.error(f"❌ فشل الرد الآلي: {e}")

if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    # تشغيل الوظائف
    post_scoop()
    auto_reply()
