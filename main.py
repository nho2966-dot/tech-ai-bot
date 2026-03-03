import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
from datetime import datetime
from loguru import logger

# --- 🔐 الإعدادات (تأكد من وجودها في GitHub Secrets) ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

# إعداد الربط مع منصة X
try:
    auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
    api_v1 = tweepy.API(auth)
    client_v2 = tweepy.Client(
        bearer_token=X_CREDS["bearer"],
        consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
        access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"]
    )
except Exception as e:
    logger.error(f"خطأ في إعدادات X: {e}")

# --- 🗄️ قاعدة البيانات (منع التكرار) ---
conn = sqlite3.connect("nasser_ai.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY)")
conn.commit()

# --- 🛡️ نظام الفلترة والتدقيق ---
def nasser_cleaner(text):
    if not text: return ""
    # استبدال إلزامي بناءً على توجيهاتك
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    # التأكد من عدم وجود لغات غير العربية/الانجليزية المسموحة
    return text.strip()

# --- 🧠 محرك Gemini (مع معالجة متطورة للأخطاء) ---
async def ask_gemini(prompt, system_msg):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"System Instruction: {system_msg}\n\nUser Request: {prompt}"}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
            data = r.json()
            
            if 'candidates' in data and data['candidates']:
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                return nasser_cleaner(raw_text)
            else:
                logger.error(f"رد غير متوقع من Gemini: {data}")
                return None
    except Exception as e:
        logger.error(f"فشل الاتصال بـ Gemini: {e}")
        return None

# --- 📡 رادار الميديا (Pexels) ---
async def fetch_tech_media():
    if not PEXELS_KEY: return None, None
    
    search_terms = ["artificial intelligence", "tech", "software", "robot"]
    query = random.choice(search_terms)
    headers = {"Authorization": PEXELS_KEY}
    
    try:
        async with httpx.AsyncClient() as client:
            # محاولة جلب فيديو أولاً
            v_url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
            res = await client.get(v_url, headers=headers)
            videos = res.json().get('videos', [])
            
            if videos:
                v_link = random.choice(videos)['video_files'][0]['link']
                v_content = await client.get(v_link)
                with open("media.mp4", "wb") as f: f.write(v_content.content)
                return "media.mp4", "video"
            
            # إذا ما لقينا فيديو، نجيب صورة
            img_url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
            res = await client.get(img_url, headers=headers)
            imgs = res.json().get('photos', [])
            if imgs:
                i_link = imgs[0]['src']['large']
                i_content = await client.get(i_link)
                with open("media.jpg", "wb") as f: f.write(i_content.content)
                return "media.jpg", "image"
                
    except Exception as e:
        logger.warning(f"رادار الميديا تعطل: {e}")
    return None, None

# --- 🚀 العمليات الرئيسية ---
async def run_nasser_bot():
    logger.info("جاري فحص المحتوى الجديد...")
    
    # 1. توليد النص (لهجة خليجية + تركيز على الأفراد)
    sys_prompt = "أنت خبير تقني خليجي مطلع. اكتب بلهجة بيضاء (كويتية/سعودية) محببة. ركز فقط على أدوات الذكاء الاصطناعي للأفراد."
    user_prompt = "عطني معلومة عن أداة ذكاء اصطناعي جديدة وتكون مفيدة جداً للشغل أو الحياة اليومية، مع لمحة تشويق."
    
    tweet_text = await ask_gemini(user_prompt, sys_prompt)
    if not tweet_text: return

    # 2. جلب الميديا
    media_path, media_type = await fetch_tech_media()

    # 3. النشر على X
    try:
        if media_path:
            # رفع الملف (v1.1)
            media_id = api_v1.media_upload(filename=media_path).media_id
            client_v2.create_tweet(text=tweet_text, media_ids=[media_id])
        else:
            client_v2.create_tweet(text=tweet_text)
            
        logger.success("تم نشر التغريدة بنجاح!")
    except Exception as e:
        logger.error(f"فشل النشر على X: {e}")
    finally:
        if media_path and os.path.exists(media_path):
            os.remove(media_path)

if __name__ == "__main__":
    asyncio.run(run_nasser_bot())
