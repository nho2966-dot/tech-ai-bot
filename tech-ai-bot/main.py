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

# ✅ تحميل الإعدادات
load_dotenv()

# إعداد نظام التسجيل الاحترافي
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("agent.log", encoding='utf-8'), logging.StreamHandler()]
)

# ✅ تهيئة عملاء X (V2 للنص و V1 للصور)
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

ARCHIVE_FILE = "published_archive.txt"

# ---------------------------------------------------------
# 1. نظام الذاكرة ومنع التكرار
# ---------------------------------------------------------
def is_duplicate(title):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return title.lower()[:60] in f.read().lower()

def save_to_archive(title):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d')}: {title}\n")

# ---------------------------------------------------------
# 2. محرك توليد المحتوى (شخصية Cyber Hunter)
# ---------------------------------------------------------
def generate_cyber_content(topic_info):
    prompt = (
        f"أنت 'Cyber Hunter': خبير تقني شاب وصائد تسريبات. الخبر هو: {topic_info}\n\n"
        "⚠️ طبق المعادلة التالية بدقة:\n"
        "1. ابدأ بـ [TITLE: عنوان قصير].\n"
        "2. النص: خطاف صادم (Hook) -> 3 نقاط مركزة (الزبدة) -> تلميحة حصرية -> رابط المصدر -> سؤال استفزازي ناري.\n"
        "3. الأسلوب: عربية بيضاء، إيموجي ذكي، ممنوع الحشو، موجه للشباب (ستوري إكس).\n"
        "4. النطاق الزمني: تعامل مع الخبر كأنه حدث في الـ 48 ساعة الماضية."
    )
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "system", "content": "أنت خبير تقني عالمي ومستفز بذكاء."},
                             {"role": "user", "content": prompt}],
                "temperature": 0.8
            }
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ فشل AI: {e}")
        return None

# ---------------------------------------------------------
# 3. الهوية البصرية (جلب صورة مدمجة آلياً)
# ---------------------------------------------------------
def get_visual_identity(category):
    temp_file = "post_img.jpg"
    keywords = f"{category},cyber,technology,dark"
    img_url = f"https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1200&auto=format&keywords={keywords}"
    try:
        res = requests.get(img_url, timeout=15)
        if res.status_code == 200:
            with open(temp_file, "wb") as f: f.write(res.content)
            media = api_v1.media_upload(filename=temp_file)
            return media.media_id, temp_file
    except: return None, None

# ---------------------------------------------------------
# 4. وظيفة النشر الاحترافي
# ---------------------------------------------------------
def execute_scoop():
    # مجالات الرصد الخاصة بك
    scenarios = [
        {"cat": "hacking", "q": "أحدث اختراق أمني عالمي أو ثغرة (Hacker News)"},
        {"cat": "smartphone", "q": "تسريب هاتف آيفون أو سامسونج قادم (9to5Mac)"},
        {"cat": "gaming", "q": "أحدث ميزة في بلايستيشن أو إكس بوكس (The Verge)"},
        {"cat": "AI", "q": "أداة ذكاء اصطناعي جديدة تهم المصممين أو المبرمجين"}
    ]
    
    selected = random.choice(scenarios)
    logging.info(f"🔎 رصد مجال: {selected['cat']}")
    
    raw_content = generate_cyber_content(selected["q"])
    if not raw_content or "TITLE:" not in raw_content: return

    # استخراج العنوان وفحصه
    title = re.search(r"TITLE: (.*)\n", raw_content).group(1).strip()
    if is_duplicate(title):
        logging.info(f"🚫 مكرر: {title}")
        return

    clean_text = raw_content.replace(f"TITLE: {title}", "").strip()
    media_id, img_path = get_visual_identity(selected["cat"])

    try:
        client.create_tweet(text=clean_text[:280], media_ids=[media_id] if media_id else None)
        save_to_archive(title)
        logging.info(f"🔥 تم النشر بنجاح: {title}")
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")
    finally:
        if img_path and os.path.exists(img_path): os.remove(img_path)

# ---------------------------------------------------------
# 5. الجدولة الذكية (وقت ذروة عُمان)
# ---------------------------------------------------------
if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    while True:
        now = datetime.now(oman_tz)
        # النشر في أوقات الذروة (صباحاً، عصراً، ومساءً)
        if now.hour in [9, 13, 17, 21, 23] and now.minute == 0:
            execute_scoop()
            time.sleep(65) # تجنب التكرار في نفس الدقيقة
        time.sleep(30)
