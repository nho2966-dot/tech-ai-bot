import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
import subprocess
from datetime import datetime
from loguru import logger

# --- 🔐 إعدادات الوصول (GitHub Secrets) ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

# إعداد مكتبات X
auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=X_CREDS["bearer"],
    consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
    access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"]
)

# --- 🗄️ نظام الذاكرة (لمنع التكرار) ---
conn = sqlite3.connect("nasser_bot.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS archive (content_hash TEXT PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY)")
conn.commit()

# --- 🛡️ الفلتر السيادي ---
def nasser_filter(text):
    if not text: return ""
    # تطبيق شرط تبديل المصطلحات
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    return text.strip()

# --- 🧠 محرك الذكاء الاصطناعي (Gemini) ---
async def ask_gemini(prompt, system_instruction):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"System: {system_instruction}\n\nUser: {prompt}"}]}]
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=payload)
            result = r.json()['candidates'][0]['content']['parts'][0]['text']
            return nasser_filter(result)
    except Exception as e:
        logger.error(f"❌ خطأ AI: {e}")
        return None

# --- 📡 الرادار المرئي (فيديو وصور) ---
async def get_visual_content():
    """يحاول جلب فيديو من Pexels، وإذا فشل يجيب صورة من Unsplash"""
    filename = None
    
    # محاولة جلب فيديو Pexels
    if PEXELS_KEY:
        queries = ["artificial intelligence", "coding", "tech", "robotics"]
        query = random.choice(queries)
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
        headers = {"Authorization": PEXELS_KEY}
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=headers)
                v_data = r.json().get('videos', [])
                if v_data:
                    v_url = random.choice(v_data)['video_files'][0]['link']
                    v_res = await client.get(v_url, follow_redirects=True)
                    filename = "media_payload.mp4"
                    with open(filename, "wb") as f: f.write(v_res.content)
                    return filename, "video"
        except: logger.warning("⚠️ فشل رادار الفيديو، الانتقال للصور...")

    # الخطة البديلة: صورة Unsplash
    try:
        img_url = "https://source.unsplash.com/featured/?technology,ai"
        async with httpx.AsyncClient() as client:
            r = await client.get(img_url, follow_redirects=True)
            filename = "media_payload.jpg"
            with open(filename, "wb") as f: f.write(r.content)
            return filename, "image"
    except: return None, None

# --- 🐦 وظائف النشر والرد ---
async def process_mentions():
    """الرد على المنشن بذكاء خليجي وعدم تكرار الرد"""
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return

        for tweet in mentions[:3]: # الرد على آخر 3 فقط لتجنب السبام
            cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),))
            if not cursor.fetchone():
                reply_text = await ask_gemini(
                    f"رد بلهجة خليجية بيضاء وذكية على هذا التعليق: {tweet.text}",
                    "أنت ناصر، خبير تقني خليجي لبق ومحب للمساعدة."
                )
                if reply_text:
                    client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    cursor.execute("INSERT INTO replies VALUES (?)", (str(tweet.id),))
                    conn.commit()
                    logger.info(f"✅ تم الرد على {tweet.id}")
                    await asyncio.sleep(20) # فاصل زمني بسيط
    except Exception as e:
        logger.error(f"⚠️ خطأ في المعالجة: {e}")

async def post_daily_tech():
    """نشر المحتوى اليومي مع الميديا"""
    media_file, media_type = await get_visual_content()
    
    prompt = "اكتب تغريدة خليجية حماسية عن أداة ذكاء اصطناعي جديدة مفيدة جداً للأفراد (ذكر اسم الأداة وفائدتها) مع إيموجي مناسب."
    content = await ask_gemini(prompt, "خبير تقني خليجي، محتواك دقيق وعملي وبعيد عن الهلوسة.")
    
    if not content: return

    try:
        media_id = None
        if media_file:
            media_id = api_v1.media_upload(filename=media_file).media_id
        
        # النشر
        if media_id:
            client_v2.create_tweet(text=content, media_ids=[media_id])
        else:
            client_v2.create_tweet(text=content)
        logger.success("🚀 تم نشر التغريدة التقنية بنجاح!")
    except Exception as e:
        logger.error(f"❌ فشل النشر: {e}")
    finally:
        if media_file and os.path.exists(media_file): os.remove(media_file)

# --- 🎬 نقطة الانطلاق ---
async def main():
    logger.info("🤖 بوت ناصر التقني بدأ العمل...")
    # 1. تنفيذ النشر اليومي
    await post_daily_tech()
    # 2. فحص والرد على المنشن
    await process_mentions()
    logger.info("🏁 انتهت المهمة بنجاح.")

if __name__ == "__main__":
    asyncio.run(main())
