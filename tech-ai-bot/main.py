import os
import tweepy
import requests
import logging
import random
import re
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
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

# 2. محرك الذكاء الاصطناعي (حقن الشخصية + السبق + السؤال الاستفزازي)
def fetch_ai_agent_response(prompt):
    try:
        current_year = datetime.now().year
        system_persona = (
            f"أنت خبير تقني شاب، صائد سبق صحفي، وجيمر محترف في عام {current_year}. "
            "مهمتك: رصد أخبار الألعاب، تحديثات X، الذكاء الاصطناعي، والأمن السيبراني. "
            "⚠️ قواعد النشر الصارمة:\n"
            "1. الهيكل: [Image URL] -> [عنوان Hook صادم] -> [3 نقاط تفصيلية] -> [نصيحة عملية] -> [رابط المصدر] -> [السؤال الناري].\n"
            "2. السؤال الختامي: يجب أن يكون استفزازياً، محفزاً، ومثيراً للجدل لزيادة التعليقات. (مثال: 'هل ما زلت تدفع لهذا التطبيق الفاشل؟' أو 'لو ما جربت هذه الميزة فإنت لسه في 2010').\n"
            "3. الصورة: اختر رابط صورة من Unsplash يعبر عن الخبر وضعه في البداية بتنسيق [Image URL: http...].\n"
            "4. الأسلوب: شبابي 'ستوري'، إيموجي ذكي، وهاشتاقات ترند عالمية."
        )
        
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [
                    {"role": "system", "content": system_persona},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.85
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ في محرك الوكيل: {e}")
        return None

# 3. وظيفة النشر الاحترافي (نص + صورة)
def publish_viral_content(full_content):
    # استخراج رابط الصورة
    img_url_match = re.search(r"\[Image URL: (https?://[^\s]+)\]", full_content)
    tweet_text = full_content
    
    media_id = None
    if img_url_match:
        img_url = img_url_match.group(1)
        tweet_text = full_content.replace(img_url_match.group(0), "").strip()
        
        try:
            img_res = requests.get(img_url, timeout=10)
            img_path = "temp_post.jpg"
            with open(img_path, "wb") as f:
                f.write(img_res.content)
            
            media = api_v1.media_upload(filename=img_path)
            media_id = [media.media_id]
            os.remove(img_path)
        except Exception as e:
            logging.error(f"⚠️ فشل تجهيز الصورة: {e}")

    try:
        client.create_tweet(text=tweet_text, media_ids=media_id)
        logging.info("🔥 تم نشر السبق بنجاح مع السؤال الاستفزازي!")
    except Exception as e:
        logging.error(f"❌ فشل النشر النهائي: {e}")

# 4. محرك التشغيل الرئيسي
if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    now_oman = datetime.now(oman_tz)
    event_name = os.getenv('GITHUB_EVENT_NAME', 'manual')
    
    logging.info(f"🕶️ الوكيل 'المستفز' في وضع العمل | الحدث: {event_name}")

    if event_name in ['workflow_dispatch', 'manual'] or now_oman.hour % 6 == 0:
        tasks = [
            "سبق صحفي عن تسريب ميزة في X تهم الجيمرز مع سؤال محفز.",
            "تحذير أمني من اختراق عالمي بأسلوب صادم وسؤال للمتابعين.",
            "أداة ذكاء اصطناعي ستجعل الموظفين التقليديين بلا عمل، مع سؤال مستفز.",
            "إطلاق لعبة عالمية منتظرة ومقارنتها بالمنافسين بأسلوب يثير الجدل."
        ]
        content = fetch_ai_agent_response(random.choice(tasks))
        if content:
            publish_viral_content(content)
