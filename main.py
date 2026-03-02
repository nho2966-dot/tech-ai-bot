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

# إعداد تويتر
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
    logger.critical(f"🛑 خطأ في API تويتر: {e}")

# --- 🗄️ قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect("nasser_tech.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, date TEXT)")
    conn.commit()
    return conn

conn = init_db()

# --- 🧠 ذكاء ناصر (مع معالجة الزحمة 429) ---
async def ask_gemini(prompt, system_role="tech_expert"):
    nasir_persona = "أنت ناصر، خبير تقني خليجي متمكن، لهجتك خليجية بيضاء وحماسية."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": f"{nasir_persona}\n\nالسياق: {system_role}\nالطلب: {prompt}"}]}]}
    
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=payload)
            
            if r.status_code == 429:
                logger.warning("⏳ تجاوزت حد الطلبات (Quota). سأنتظر 60 ثانية...")
                await asyncio.sleep(60) # انتظر دقيقة كاملة
                return None
                
            data = r.json()
            if r.status_code == 200 and 'candidates' in data:
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            logger.error(f"⚠️ فشل استجابة AI: {data.get('message', 'خطأ غير معروف')}")
            return None
    except Exception as e:
        logger.error(f"❌ خطأ تقني في Gemini: {e}")
        return None

# --- 🎥 جلب الفيديو ---
async def download_video():
    sources = ["https://www.youtube.com/@Omardizer", "https://www.youtube.com/@FaisalAlsaif"]
    filename = f"vid_{random.getrandbits(16)}.mp4"
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings", "--format", "mp4",
        "--max-filesize", "8M", "--playlist-items", "1",
        "--download-sections", "*0-15", "-o", filename, random.choice(sources)
    ]
    try:
        process = await asyncio.create_subprocess_exec(*cmd)
        await asyncio.wait_for(process.wait(), timeout=120)
        return filename if os.path.exists(filename) else None
    except: return None

# --- 🐦 النشر والردود ---
async def post_to_x(content, video_path=None):
    try:
        media_id = None
        if video_path:
            media = api_v1.media_upload(filename=video_path, media_category='tweet_video', chunked=True)
            media_id = media.media_id
            time.sleep(15) 
        client_v2.create_tweet(text=content, media_ids=[media_id] if media_id else None)
        logger.success("✅ تم النشر بنجاح")
    except Exception as e:
        logger.error(f"❌ فشل النشر: {e}")

async def handle_mentions():
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return

        for tweet in mentions[:2]: # تقليل العدد لتقليل استهلاك الكوتا
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),))
            if cursor.fetchone(): continue

            reply_text = await ask_gemini(f"رد على: {tweet.text}", "رد منشن")
            if reply_text:
                client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                cursor.execute("INSERT INTO replies VALUES (?,?)", (str(tweet.id), datetime.now().isoformat()))
                conn.commit()
                logger.info(f"📩 تم الرد على {tweet.id}")
                await asyncio.sleep(30) # زيادة الفاصل الزمني
