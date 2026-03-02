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

# --- 🔐 الإعدادات ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

# إعداد تويتر (Tweepy)
try:
    auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
    api_v1 = tweepy.API(auth)
    client_v2 = tweepy.Client(
        bearer_token=X_CREDS["bearer"],
        consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
        access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"]
    )
    logger.info("📡 تم تهيئة اتصال تويتر بنجاح")
except Exception as e:
    logger.critical(f"🛑 خطأ في إعدادات API تويتر: {e}")

# --- 🗄️ قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect("nasser_tech.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, date TEXT)")
    conn.commit()
    return conn

conn = init_db()

# --- 🧠 ذكاء ناصر (Gemini) ---
async def ask_gemini(prompt, system_role="tech_expert"):
    nasir_persona = (
        "أنت ناصر، خبير تقني خليجي متمكن. أسلوبك: لهجة خليجية بيضاء، حماسي، بسيط. "
        "تستخدم كلمات مثل 'يا هلا'، 'شي بطل'، 'لا يفوتكم'. "
        "تشرح الأدوات بأسلوب عملي بعيداً عن الفصحى الجامدة."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"{nasir_persona}\n\nسياق الموضوع: {system_role}\nالطلب: {prompt}"}]}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=payload)
            data = r.json()
            
            # فحص دقيق للرد لتجنب KeyError 'candidates'
            if r.status_code == 200 and 'candidates' in data and data['candidates']:
                res_text = data['candidates'][0]['content']['parts'][0]['text']
                return res_text.strip()
            else:
                logger.error(f"⚠️ فشل استجابة AI: {data.get('error', 'تنسيق غير متوقع')}")
                return None
    except Exception as e:
        logger.error(f"❌ خطأ تقني في Gemini: {e}")
        return None

# --- 🎥 جلب الفيديوهات ---
async def download_video():
    sources = ["https://www.youtube.com/@Omardizer", "https://www.youtube.com/@FaisalAlsaif"]
    target = random.choice(sources)
    filename = f"vid_{random.getrandbits(16)}.mp4"
    
    # تحميل أول 15 ثانية فقط لضمان سرعة الرفع وتجنب رفض تويتر
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings", "--format", "mp4",
        "--max-filesize", "8M", "--playlist-items", "1",
        "--download-sections", "*0-15", "-o", filename, target
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(*cmd)
        await asyncio.wait_for(process.wait(), timeout=120)
        return filename if os.path.exists(filename) else None
    except:
        return None

# --- 🐦 النشر والردود الذكية ---
async def post_to_x(content, video_path=None):
    try:
        media_id = None
        if video_path:
            logger.info("📤 جاري رفع الفيديو...")
            media = api_v1.media_upload(filename=video_path, media_category='tweet_video', chunked=True)
            media_id = media.media_id
            time.sleep(15) # انتظار المعالجة

        client_v2.create_tweet(text=content, media_ids=[media_id] if media_id else None)
        logger.success("✅ تم نشر التغريدة بنجاح")
    except Exception as e:
        if "403" in str(e):
            logger.error("🛑 خطأ 403: تويتر ما زال يرفض الكتابة. (تأكد من تجديد الـ Tokens)")
        else:
            logger.error(f"❌ فشل النشر: {e}")

async def handle_mentions():
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return

        for tweet in mentions[:3]:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),))
            if cursor.fetchone(): continue

            reply_text = await ask_gemini(f"رد بلهجة ناصر على: {tweet.text}", "رد على منشن")
            if reply_text:
                client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                cursor.execute("INSERT INTO replies VALUES (?,?)", (str(tweet.id), datetime.now().isoformat()))
                conn.commit()
                logger.info(f"📩 تم الرد على {tweet.id}")
                await asyncio.sleep(15)
    except Exception as e:
        logger.error(f"❌ خطأ في المنشن: {e}")

# --- 🚀 التشغيل الدوري ---
async def main():
    logger.info("🤖 بوت ناصر التقني بدأ العمل...")
    
    while True:
        # 1. نشر تغريدة جديدة (كل دورة)
        content = await ask_gemini("اكتب تغريدة عن أداة ذكاء اصطناعي مفيدة للأفراد", "تغريدة عامة")
        if content:
            video = await download_video()
            await post_to_x(content, video)
            if video and os.path.exists(video): os.remove(video)

        # 2. مراقبة المنشن والرد (6 مرات كل 10 دقائق = ساعة كاملة)
        for _ in range(6):
            await handle_mentions()
            await asyncio.sleep(600) # انتظار 10 دقائق

if __name__ == "__main__":
    asyncio.run(main())
