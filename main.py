import os
import asyncio
import httpx
import tweepy
import sqlite3
import hashlib
import random
import re
import difflib
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

auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=X_CREDS["bearer"],
    consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
    access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"]
)

# --- 🗄️ قاعدة البيانات ---
conn = sqlite3.connect("nasser_final_fix.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS archive (hash TEXT PRIMARY KEY, idea TEXT, date TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, date TEXT)")
conn.commit()

# --- 🛡️ الفلاتر ---
def nasser_filter(text):
    if not text: return ""
    return text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته").strip()

async def ask_gemini(prompt, system_msg):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": f"{system_msg}\n\n{prompt}"}]}]}
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=payload)
            data = r.json()
            return nasser_filter(data['candidates'][0]['content']['parts'][0]['text'])
    except:
        return None

# --- 📡 الرادار ---
def download_tech_video():
    sources = [
        "https://www.youtube.com/@Omardizer",
        "https://www.youtube.com/@FaisalAlsaif",
        "https://www.youtube.com/@MKBHD",
        "https://www.youtube.com/@theverge"
    ]
    target = random.choice(sources)
    filename = f"vid_{random.randint(10,99)}.mp4"
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings", "--format", "mp4",
        "--max-filesize", "15M", "--playlist-items", "1", "--no-playlist",
        "--download-sections", "*0-30", "-o", filename, target
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120)
        return filename if os.path.exists(filename) else None
    except:
        return None

# --- 🚀 المهمة الرئيسية ---
async def run_bot():
    # 1. النشر التلقائي
    video = download_tech_video()
    media_id = None
    if video:
        try:
            media_id = api_v1.media_upload(filename=video, media_category='tweet_video').media_id
            logger.info("✅ تم رفع الفيديو بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل رفع الفيديو: {e}")

    content = await ask_gemini("اكتب تغريدة خليجية مشوقة جداً عن أداة ذكاء اصطناعي جديدة مفيدة للأفراد", "خبير تقني خليجي")
    
    if content:
        try:
            if media_id:
                client_v2.create_tweet(text=content, media_ids=[media_id])
            else:
                client_v2.create_tweet(text=content)
            logger.success("✅ تم نشر التغريدة")
        except Exception as e:
            logger.error(f"❌ فشل النشر: {e}")

    # 2. الردود الذكية (تم تصحيح الـ Try-Except هنا)
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if mentions:
            for tweet in mentions[:2]: # الرد على آخر 2 فقط للأمان
                cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),))
                if not cursor.fetchone():
                    reply = await ask_gemini(f"رد بذكاء خليجي على: {tweet.text}", "تقني لبق")
                    if reply:
                        await asyncio.sleep(30) # فاصل زمني
                        client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                        cursor.execute("INSERT INTO replies VALUES (?,?)", (str(tweet.id), datetime.now().isoformat()))
                        conn.commit()
                        logger.info(f"✅ تم الرد على {tweet.id}")
    except Exception as e:
        logger.warning(f"⚠️ مشكلة في الردود: {e}")

    if video and os.path.exists(video):
        os.remove(video)

if __name__ == "__main__":
    asyncio.run(run_bot())
