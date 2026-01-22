import os
import tweepy
import requests
import logging
import random
import re
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# إعدادات التسجيل والـوُضُـوح
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

ARCHIVE_FILE = "published_archive.txt"

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

# 2. نظام الذاكرة لمنع تكرار المـوُضـوُعات
def is_duplicate(content_title):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return content_title.lower()[:60] in f.read().lower()

def save_to_archive(content_title):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d')}: {content_title}\n")

# 3. محرك الذكاء الاصطناعي (ضبط النطاق الزمني 48-72 ساعة)
def fetch_tech_scoop(category_desc):
    try:
        # تحديد النافذة الزمنية بدقة في البرومبت
        system_persona = (
            f"أنت خبير تقني عالمي. اليوم هو {datetime.now().strftime('%Y-%m-%d')}. "
            "⚠️ تعليمات البحث والنشر:\n"
            "1. النطاق الزمني: ابحث عن الأخبار والتسريبات التي حدثت خلال الـ 24 إلى 72 ساعة الماضية فقط.\n"
            "2. المحتوى: ركز على الألعاب، الأمن السيبراني، ومنصات التواصل الاجتماعي، والذكاء الاصطناعي X بأسلوب حاد ومختصر جداً.\n"
            "3. الفلترة: ممنوع الحشو، وممنوع الأخبار التي مضى عليها أكثر من 3 أيام.\n"
            "4. الهيكل: [TITLE: عنوان الخبر] ثم (Hook صادم -> 3 تفاصيل تقنية -> رابط المصدر -> سؤال مستفز)."
        )
        
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "system", "content": system_persona},
                             {"role": "user", "content": f"ارصد سبقاً صحفياً في: {category_desc}"}],
                "temperature": 0.7
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ AI: {e}")
        return None

# 4. وظيفة جلب الصورة ونشر التغريدة
def publish_with_media(raw_output, category_key):
    title_match = re.search(r"TITLE: (.*)\n", raw_output)
    if not title_match: return

    title = title_match.group(1).strip()
    if is_duplicate(title):
        logging.info(f"🚫 مكرر: {title}")
        return

    clean_text = raw_output.replace(f"TITLE: {title}", "").strip()
    
    # جلب صورة احترافية آلياً في الخلفية
    media_ids = []
    temp_img = "vibrant_news.jpg"
    try:
        img_url = f"https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1200&auto=format&keywords={category_key},technology"
        img_data = requests.get(img_url).content
        with open(temp_img, "wb") as f: f.write(img_data)
        media = api_v1.media_upload(filename=temp_img)
        media_ids = [media.media_id]
    except: pass

    try:
        client.create_tweet(text=clean_text, media_ids=media_ids)
        save_to_archive(title)
        logging.info(f"✅ تم النشر: {title}")
    finally:
        if os.path.exists(temp_img): os.remove(temp_img)

# 5. التشغيل
if __name__ == "__main__":
    scenarios = [
        {"key": "cybersecurity", "desc": "أحدث اختراق أو ثغرة أمنية في آخر 72 ساعة"},
        {"key": "gaming", "desc": "أحدث تسريب أو إطلاق في عالم الألعاب خلال يومين"},
        {"key": "X_platform", "desc": "ميزات جديدة تم رصدها في X مؤخراً"}
    ]
    
    selected = random.choice(scenarios)
    output = fetch_tech_scoop(selected["desc"])
    if output:
        publish_with_media(output, selected["key"])
