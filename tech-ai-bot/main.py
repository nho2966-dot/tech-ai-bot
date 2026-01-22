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
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

# 2. محرك الذكاء الاصطناعي (قناص الأخبار الحديثة)
def fetch_ai_agent_response(category_desc):
    try:
        current_year = datetime.now().year
        system_persona = (
            f"أنت وكيل تقني عالمي متخصص في رصد السبق الصحفي لعام {current_year}. "
            "مهمتك: كتابة خبر حصري جداً، حديث (آخر 24 ساعة)، ومكثف.\n"
            "⚠️ القواعد الصارمة:\n"
            "- لا مقدمات ولا حشو: ادخل في صلب الخبر فوراً بأسلوب 'الخطاف'.\n"
            "- الهيكل: عنوان مثير -> 3 معلومات حصرية وفنية -> رابط المصدر -> سؤال استفزازي.\n"
            "- تجنب المعلومات المستهلكة أو القديمة نهائياً.\n"
            "- اللغة: عربية بيضاء احترافية وموجزة."
        )
        
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [
                    {"role": "system", "content": system_persona},
                    {"role": "user", "content": f"ارصد أحدث سبق صحفي في مجال: {category_desc}"}
                ],
                "temperature": 0.8
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ AI: {e}")
        return None

# 3. وظيفة جلب الصورة الذكية والنشر
def publish_tech_scoop(text, search_term):
    media_ids = []
    temp_file = "latest_tech_news.jpg"
    
    try:
        # جلب صورة احترافية مرتبطة بالمجال المحدد آلياً
        img_url = f"https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80&keywords={search_term}"
        # ملاحظة: تم استخدام كلمات مفتاحية ديناميكية لضمان صلة الصورة بالخبر
        img_res = requests.get(img_url, timeout=15)
        
        if img_res.status_code == 200:
            with open(temp_file, "wb") as f:
                f.write(img_res.content)
            media = api_v1.media_upload(filename=temp_file)
            media_ids = [media.media_id]
            logging.info(f"📸 تم إرفاق صورة عالية الجودة لمجال: {search_term}")
    except Exception as e:
        logging.error(f"⚠️ فشل جلب الصورة: {e}")

    try:
        client.create_tweet(text=text, media_ids=media_ids)
        logging.info("🔥 تم نشر السبق التقني بنجاح!")
        if os.path.exists(temp_file): os.remove(temp_file)
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

# 4. محرك الرصد (تحديد المسارات الخمسة)
if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    now = datetime.now(oman_tz)
    
    # خريطة الرصد المحددة من قبلك
    scenarios = [
        {"key": "cybersecurity,hacking", "desc": "الأمن السيبراني وأحدث الاختراقات الأمنية العالمية"},
        {"key": "gaming,ps5,xbox", "desc": "الألعاب الإلكترونية وأحدث ما توصلت إليه الصناعة عالمياً"},
        {"key": "socialmedia,twitter,meta", "desc": "أحدث ميزات وتسريبات منصات التواصل الاجتماعي (X, Meta, etc)"},
        {"key": "smartphone,iphone,android", "desc": "أحدث تكنولوجيا الأجهزة الذكية والهواتف النقالة المسربة"},
        {"key": "artificialintelligence,tech", "desc": "توظيف الذكاء الاصطناعي في الأجهزة والمنصات الحديثة"}
    ]
    
    selected = random.choice(scenarios)
    event_name = os.getenv('GITHUB_EVENT_NAME', 'manual')
    
    # النشر اليدوي أو المجدول (كل 6 ساعات)
    if event_name in ['workflow_dispatch', 'manual'] or now.hour % 6 == 0:
        content = fetch_ai_agent_response(selected["desc"])
        if content:
            publish_tech_scoop(content, selected["key"])
