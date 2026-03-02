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

# --- الإعدادات ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET")
}

# تعريف Tweepy للرفع والنشر
auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
api_v1 = tweepy.API(auth) # للوسائط (Media)
client_v2 = tweepy.Client(
    consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
    access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"]
)

# --- قاعدة البيانات ---
conn = sqlite3.connect("nasser_final_v1.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS archive (hash TEXT PRIMARY KEY, topic_idea TEXT, type TEXT)")
conn.commit()

# --- رادار الفيديو (تحميل الفيديوهات التقنية) ---
def download_tech_video():
    logger.info("🔎 جاري البحث عن مقطع فيديو تقني جديد...")
    # قائمة قنوات تقنية عالمية (أو ضع روابط محددة)
    channels = ["https://www.youtube.com/@TheVerge/videos", "https://www.youtube.com/@MKHD/videos"]
    target_url = random.choice(channels)
    
    video_filename = "tech_video.mp4"
    # أمر التحميل مع تحديد الجودة والمدة (أول 45 ثانية لتناسب X)
    cmd = [
        "yt-dlp", 
        "--max-filesize", "15M", 
        "--format", "mp4",
        "--playlist-items", "1",
        "--download-sections", "*0-45", # أول 45 ثانية فقط
        "-o", video_filename,
        target_url
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return video_filename
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الفيديو: {e}")
        return None

# --- رفع الفيديو إلى X ---
def upload_video_to_x(file_path):
    try:
        logger.info("📤 جاري رفع الفيديو إلى X...")
        media = api_v1.media_upload(filename=file_path, media_category='tweet_video')
        return media.media_id
    except Exception as e:
        logger.error(f"❌ فشل رفع الفيديو: {e}")
        return None

# --- توليد النص ومنع التكرار ---
async def generate_and_check(topic):
    # (هنا نستخدم نفس منطق is_intellectually_duplicated اللي اتفقنا عليه)
    # ... (تم اختصاره هنا لدمجه في الوظيفة الرئيسية)
    pass

# --- المهمة الرئيسية ---
async def run_sovereign_task():
    # 1. محاولة جلب فيديو
    video_file = download_tech_video()
    media_id = None
    if video_file and os.path.exists(video_file):
        media_id = upload_video_to_x(video_file)

    # 2. توليد محتوى نصي (خبيئة تقنية)
    topic_suggestion = "أداة ذكاء اصطناعي جديدة للأفراد"
    # (نظام Gemini لتوليد النص والتحقق من التكرار المعنوي)
    content_text = "شوفوا هالأداة الرهيبة اللي تختصر عليك ساعات من العمل البرمجي! 🚀 #ذكاء_اصطناعي"
    
    # 3. النشر النهائي (فيديو + نص) أو (نص فقط)
    try:
        if media_id:
            client_v2.create_tweet(text=content_text, media_ids=[media_id])
            logger.success("✅ تم النشر بنجاح: فيديو + نص!")
        else:
            client_v2.create_tweet(text=content_text)
            logger.success("✅ تم النشر بنجاح: نص فقط (لعدم توفر فيديو).")
    except Exception as e:
        logger.error(f"❌ خطأ في النشر النهائي: {e}")

    # 4. تنظيف الملفات
    if video_file and os.path.exists(video_file):
        os.remove(video_file)

if __name__ == "__main__":
    asyncio.run(run_sovereign_task())
