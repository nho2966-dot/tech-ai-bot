import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
import time
import subprocess
from datetime import datetime
from loguru import logger

# --- 🔐 الإعدادات (تأكد من ضبط المتغيرات في البيئة) ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

# إعداد Tweepy (V1 للوسائط و V2 للتغريدات)
auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=X_CREDS["bearer"],
    consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
    access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"]
)

# --- 🗄️ قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect("nasser_tech.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS archive (id TEXT PRIMARY KEY, content TEXT, date TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, date TEXT)")
    conn.commit()
    return conn

conn = init_db()

# --- 🧠 ذكاء ناصر (Gemini) ---
async def ask_gemini(prompt, system_role="tech_expert"):
    # شخصية ناصر الخليجي
    nasir_persona = (
        "أنت ناصر، خبير تقني خليجي متمكن. أسلوبك: لهجة خليجية بيضاء، محفز، بسيط، وقريب من الناس. "
        "تستخدم عبارات مثل: 'يا جماعة الخير'، 'لقطة اليوم'، 'خلوكم قريبين'. "
        "لا تستخدم الفصحى المعقدة. إذا شرحت أداة، ركز على كيف تسهل حياة الشخص."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"{nasir_persona}\n\nالسياق: {system_role}\nالطلب: {prompt}"}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
            data = r.json()
            res = data['candidates'][0]['content']['parts'][0]['text']
            # تنظيف النص من أي فلاتر غير مرغوبة
            return res.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي").strip()
    except Exception as e:
        logger.error(f"❌ خطأ AI: {e}")
        return None

# --- 🎥 رادار الفيديو ---
async def download_video():
    sources = [
        "https://www.youtube.com/@Omardizer", 
        "https://www.youtube.com/@FaisalAlsaif",
        "https://www.youtube.com/@TheVerge"
    ]
    target = random.choice(sources)
    filename = f"nasser_vid_{random.getrandbits(16)}.mp4"
    
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings", "--format", "mp4",
        "--max-filesize", "15M", "--playlist-items", "1",
        "--download-sections", "*0-25", "-o", filename, target
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        return filename if os.path.exists(filename) else None
    except:
        return None

# --- 🐦 وظائف النشر والردود ---
async def post_to_x(content, video_path=None):
    try:
        media_id = None
        if video_path:
            logger.info("📤 جاري رفع الفيديو بنظام الأجزاء...")
            # استخدام chunked=True لضمان رفع الملفات الكبيرة بنجاح
            media = api_v1.media_upload(filename=video_path, media_category='tweet_video', chunked=True)
            media_id = media.media_id
            
            # انتظار معالجة الفيديو في سيرفرات تويتر
            logger.info("⏳ انتظار معالجة الفيديو...")
            time.sleep(15) 

        response = client_v2.create_tweet(text=content, media_ids=[media_id] if media_id else None)
        logger.success(f"✅ تم النشر! ID: {response.data['id']}")
        return response.data['id']
    except Exception as e:
        logger.error(f"❌ فشل النشر: {e}")
        return None

async def handle_mentions():
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id, tweet_fields=['text', 'author_id']).data
        
        if not mentions: return

        for tweet in mentions[:5]: # معالجة آخر 5 منشن فقط لتجنب الحظر
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),))
            if cursor.fetchone(): continue

            # هل السائل يطلب رابط؟
            is_asking_link = any(word in tweet.text.lower() for word in ["رابط", "لينك", "وين", "اسم", "link", "url"])
            
            context = "رد ذكي وقصير"
            if is_asking_link:
                context = "رد على شخص يطلب رابط الأداة. أخبره أنك ستحاول توفيره قريباً أو ابحث له عن اسم الأداة المقترحة."

            reply_text = await ask_gemini(f"المنشن: {tweet.text}", context)
            
            if reply_text:
                client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                cursor.execute("INSERT INTO replies VALUES (?,?)", (str(tweet.id), datetime.now().isoformat()))
                conn.commit()
                logger.info(f"📩 تم الرد على: {tweet.id}")
                await asyncio.sleep(20) # فاصل زمني بين الردود
    except Exception as e:
        logger.error(f"❌ خطأ في الردود: {e}")

# --- 🚀 المحرك الرئيسي ---
async def main():
    logger.info("🤖 تشغيل بوت ناصر التقني...")
    
    while True:
        # 1. توليد ونشر محتوى جديد
        topics = ["أداة AI جديدة", "تطبيق يختصر الوقت", "موقع ذكاء اصطناعي للصور", "تقنية بطلة للطلاب"]
        prompt = f"اكتب تغريدة عن {random.choice(topics)} مع شرح بسيط وفائدة ملموسة."
        
        content = await ask_gemini(prompt, "نشر تغريدة جديدة")
        
        if content:
            video = await download_video()
            await post_to_x(content, video)
            if video and os.path.exists(video): os.remove(video)

        # 2. تفقد الردود والمنشن (لمدة ساعة قبل التغريدة التالية)
        for _ in range(12): # 12 مرة كل 5 دقائق = ساعة
            await handle_mentions()
            await asyncio.sleep(300) # انتظار 5 دقائق

if __name__ == "__main__":
    asyncio.run(main())
