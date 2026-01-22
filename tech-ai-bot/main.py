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
    format='%(asctime)s - [CYBER-HUNTER-MASTER] - %(message)s',
    handlers=[logging.FileHandler("agent.log", encoding='utf-8'), logging.StreamHandler()]
)

# ✅ تهيئة الوصول لمنصة X (V2 للنص و V1 للصور)
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

ARCHIVE_FILE = "published_archive.txt"

# ---------------------------------------------------------
# 1. نظام الذاكرة والأرشفة
# ---------------------------------------------------------
def is_duplicate(identifier):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return identifier.lower()[:60] in f.read().lower()

def save_to_archive(identifier):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {identifier}\n")

# ---------------------------------------------------------
# 2. محرك توليد المحتوى (الشخصية والصرامة)
# ---------------------------------------------------------
def generate_ai_content(prompt_type, context_data=""):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        system_persona = (
            f"أنت 'Cyber Hunter' - خبير استخبارات تقنية. الوقت: {current_time}.\n"
            "⚠️ القواعد الصارمة:\n"
            "1. المصادر: (Reuters Tech, BleepingComputer, 9to5Mac, GitHub Leaks, Black Hat research).\n"
            "2. الصرامة: اذكر أسماء شركات، أرقام إصدارات، ثغرات CVE، أو أرقام أداء. ممنوع الحشو الإنشائي.\n"
            "3. النطاق الزمني: أخبار الـ 48-72 ساعة الماضية فقط.\n"
            "4. الهيكل: [TITLE: ناري] -> Hook صادم -> 3 نقاط دسمة -> تلميحة للمحترفين -> 🔗 رابط المصدر -> #هاشتاج."
        )

        if prompt_type == "post":
            user_msg = f"حلل وانشر أحدث سبق صحفي صلب وموثوق حول: {context_data}"
        else:
            user_msg = f"رد بذكاء وتقنية واختصار مستفز على هذا المنشن: '{context_data}'"

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "system", "content": system_persona},
                             {"role": "user", "content": user_msg}],
                "temperature": 0.4 if prompt_type == "post" else 0.7
            },
            timeout=30
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ فشل AI: {e}")
        return None

# ---------------------------------------------------------
# 3. الهوية البصرية (Visual Engine)
# ---------------------------------------------------------
def get_visual_id(keyword):
    path = "temp_identity.jpg"
    try:
        url = f"https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80&keywords={keyword},cyber,tech"
        img_res = requests.get(url, timeout=15)
        with open(path, "wb") as f: f.write(img_res.content)
        media = api_v1.media_upload(filename=path)
        return media.media_id, path
    except: return None, None

# ---------------------------------------------------------
# 4. وظيفة النشر (The Publisher)
# ---------------------------------------------------------
def post_scoop():
    scenarios = [
        {"cat": "hacking", "q": "ثغرة Zero-day نشطة أو اختراق عالمي ضخم (CVE)"},
        {"cat": "leaks", "q": "تسريبات كود أو ميزات مخفية في تطبيقات شهيرة"},
        {"cat": "hardware", "q": "أداء معالجات قادمة أو قطع تقنية ثورية"},
        {"cat": "AI", "q": "ترند ذكاء اصطناعي يمس الخصوصية أو يغير العمل"}
    ]
    
    selected = random.choice(scenarios)
    content = generate_ai_content("post", selected["q"])
    
    if not content or "TITLE:" not in content or "http" not in content:
        logging.warning("⚠️ الخبر غير مكتمل أو يفتقر لمصدر.")
        return

    title = re.search(r"TITLE: (.*)\n", content).group(1).strip()
    if is_duplicate(title): return

    clean_text = content.replace(f"TITLE: {title}", "").strip()
    media_id, img_path = get_visual_id(selected["cat"])

    try:
        client.create_tweet(text=clean_text[:280], media_ids=[media_id] if media_id else None)
        save_to_archive(title)
        logging.info(f"🔥 تم نشر سبق صحفي: {title}")
    finally:
        if img_path and os.path.exists(img_path): os.remove(img_path)

# ---------------------------------------------------------
# 5. وظيفة الردود الذكية (The Responder)
# ---------------------------------------------------------
def auto_reply():
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(id=me.id, max_results=5)
        
        if not mentions.data: return

        for tweet in mentions.data:
            reply_id = f"reply_{tweet.id}"
            if is_duplicate(reply_id): continue

            reply_text = generate_ai_content("reply", tweet.text)
            if reply_text:
                client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                save_to_archive(reply_id)
                logging.info(f"💬 تم الرد على المنشن: {tweet.id}")
    except Exception as e:
        logging.error(f"❌ فشل الردود: {e}")

# ---------------------------------------------------------
# 6. الحلقة الرئيسية (Execution Loop)
# ---------------------------------------------------------
if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    logging.info("🚀 Cyber Hunter Master Code is RUNNING...")
    
    while True:
        now = datetime.now(oman_tz)
        
        # النشر في ساعات الذروة (9ص، 12م، 4م، 8م، 11م)
        if now.hour in [9, 12, 16, 20, 23] and now.minute == 0:
            post_scoop()
        
        # الرد على المتابعين كل 15 دقيقة
        if now.minute % 15 == 0:
            auto_reply()
            
        time.sleep(60)
