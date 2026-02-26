import os
import asyncio
import httpx
import tweepy
import sqlite3
import hashlib
import random
import re
import subprocess
import yt_dlp
import time
from datetime import datetime
from loguru import logger

# =========================================================
# 🔐 KEYS & AUTH
# =========================================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
XAI_KEY = os.getenv("XAI_API_KEY")
QWEN_KEY = os.getenv("QWEN_API_KEY")
X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

auth = tweepy.OAuth1UserHandler(X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S)
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=X_KEY, consumer_secret=X_SECRET,
    access_token=X_TOKEN, access_token_secret=X_ACCESS_S,
    wait_on_rate_limit=True 
)

# =========================================================
# 🗄 DATABASE
# =========================================================
conn = sqlite3.connect("nasser_sovereign_flexible.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS published (hash TEXT PRIMARY KEY, time TEXT)")
conn.commit()

# =========================================================
# ⚙️ CONFIG
# =========================================================
daily_videos_count = 1
video_length_seconds = 45
tweets_per_thread = 3

# =========================================================
# 🛡 FIXED FILTER (تم إصلاح الخطأ هنا)
# =========================================================
def nasser_filter(text):
    if text is None or not isinstance(text, str): 
        return ""
    
    # استبدال المصطلح المتفق عليه
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    
    # قائمة الكلمات الممنوعة
    banned = ["stock","market","investment","funding","revenue","profit","سهم","تداول","عملة","cryptocurrency","بيتكوين"]
    
    # تنظيف النص من الكلمات الممنوعة
    for word in banned: 
        text = re.sub(rf"\b{word}\b", "", text, flags=re.IGNORECASE)
    
    # إزالة الرموز الغريبة والإبقاء على الحروف والأرقام لضمان عدم تعطل التغريدة
    text = re.sub(r'[^\u0600-\u06FFa-zA-Z0-9\s\.\!\?\(\)\،\:\-]', '', text)
    
    return text.strip()

# =========================================================
# 🧠 SOVEREIGN BRAIN
# =========================================================
class SovereignBrain:
    async def generate(self, prompt, system_msg):
        brains = [
            ("GROK", "https://api.x.ai/v1/chat/completions", {"Authorization": f"Bearer {XAI_KEY}"}, "grok-beta"),
            ("OPENAI", "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {OPENAI_KEY}"}, "gpt-4o-mini")
        ]
        for name, url, headers, model in brains:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    payload = {
                        "model": model,
                        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
                    }
                    r = await client.post(url, headers=headers, json=payload)
                    r.raise_for_status()
                    res = r.json()['choices'][0]['message']['content']
                    if res: return res
            except Exception as e:
                logger.warning(f"⚠️ Brain {name} failed: {e}")
                continue
        return "خبايا تقنية جديدة نكشفها لكم في هذا المقطع.."

brain = SovereignBrain()

# =========================================================
# 🎥 MULTI-SOURCE RADAR
# =========================================================
TRUSTED_CHANNELS = [
    "https://www.youtube.com/@mkbhd",
    "https://www.youtube.com/@Mrwhosetheboss",
    "https://www.youtube.com/@ProperHonestTech",
    "https://www.youtube.com/@HowToMen",
    "https://www.youtube.com/@MattWolfe",
    "https://www.youtube.com/@TheAIAdvantage"
]

def fetch_tech_video():
    logger.info("🔎 البحث عن خبايا تقنية جديدة...")
    ydl_opts = {'quiet': True, 'extract_flat': True, 'daterange': yt_dlp.utils.DateRange('now-2days','now')}
    random.shuffle(TRUSTED_CHANNELS)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for channel in TRUSTED_CHANNELS:
            try:
                res = ydl.extract_info(channel, download=False)
                if 'entries' in res and res['entries']:
                    for video in res['entries'][:5]:
                        title = video.get('title','')
                        v_url = video.get('url')
                        if not title or not v_url: continue
                        
                        if any(w in title.lower() for w in ["stock","market","earnings","invest"]):
                            continue
                            
                        v_hash = hashlib.sha256(title.encode()).hexdigest()
                        cursor.execute("SELECT hash FROM published WHERE hash=?", (v_hash,))
                        if cursor.fetchone(): continue 
                            
                        return {"title": title, "url": v_url, "hash": v_hash}
            except Exception as e:
                logger.warning(f"⚠️ فشل الجلب من {channel}: {e}")
    return None

# =========================================================
# 🎬 VIDEO PROCESSING
# =========================================================
def process_video(url):
    logger.info("🎬 تحميل ومعالجة الفيديو...")
    output_raw = "raw_vid.mp4"
    output_final = "nasser_vid.mp4"
    
    if os.path.exists(output_raw): os.remove(output_raw)
    if os.path.exists(output_final): os.remove(output_final)
    
    ydl_opts = {'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', 'outtmpl': output_raw, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    
    cmd = [
        "ffmpeg", "-y", "-i", output_raw, "-t", str(video_length_seconds),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-c:a", "aac", "-b:a", "128k", output_final
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_final

# =========================================================
# 🐦 THREAD POSTING
# =========================================================
async def post_nasser_thread(title, video_path):
    # توليد المحتوى
    prompt = f"حول هذا الموضوع التقني إلى سلسلة تغريدات (Thread) خليجية عن الخبايا: {title}. قسمها لـ {tweets_per_thread} تغريدات منفصلة بأسطر فارغة."
    system = "أنت ناصر، خبير خبايا الأجهزة وأسرار الإنترنت والذكاء الاصطناعي وأحدث أدواته. استعمل لهجة خليجية مرموقة."
    
    raw_content = await brain.generate(prompt, system)
    # تنظيف المحتوى وتقسيمه
    raw_tweets = [t.strip() for t in raw_content.split('\n\n') if t.strip()]
    tweets = [nasser_filter(t) for t in raw_tweets][:tweets_per_thread]
    
    if not tweets:
        tweets = ["خبايا تقنية جديدة نكشفها لكم في هذا المقطع! #تقنية"]

    logger.info("🐦 رفع الفيديو إلى منصة X...")
    media = api_v1.media_upload(video_path, media_category='tweet_video', chunked=True)
    
    # انتظار المعالجة (Loop محصن)
    check_count = 0
    while check_count < 20:
        status = api_v1.get_media_upload_status(media.media_id)
        state = status.processing_info.get("state")
        if state == "succeeded":
            break
        elif state == "failed":
            raise Exception("فشلت منصة X في معالجة الفيديو")
        
        logger.info(f"⏳ معالجة الفيديو مستمرة... (محاولة {check_count+1})")
        time.sleep(10)
        check_count += 1
    
    # نشر السلسلة
    logger.info("🚀 نشر السلسلة...")
    first_tweet = client_v2.create_tweet(text=tweets[0][:280], media_ids=[media.media_id])
    last_id = first_tweet.data['id']
    
    for i in range(1, len(tweets)):
        time.sleep(2) # تأخير بسيط لضمان الترتيب
        reply = client_v2.create_tweet(text=tweets[i][:280], in_reply_to_tweet_id=last_id)
        last_id = reply.data['id']
    
    logger.success("✅ تم نشر السلسلة التقنية بنجاح!")

# =========================================================
# 🚀 EXECUTION
# =========================================================
async def run_daily_task():
    video_data = fetch_tech_video()
    if not video_data:
        logger.info("⚠️ لا يوجد محتوى جديد يطابق الشروط حالياً.")
        return

    try:
        final_vid = process_video(video_data['url'])
        await post_nasser_thread(video_data['title'], final_vid)
        
        # تسجيل النجاح
        cursor.execute("INSERT INTO published VALUES (?,?)", (video_data['hash'], datetime.utcnow().isoformat()))
        conn.commit()
        
        # تنظيف الملفات
        for f in ["raw_vid.mp4", "nasser_vid.mp4"]:
            if os.path.exists(f): os.remove(f)
            
    except Exception as e:
        logger.error(f"❌ فشل السكربت: {e}")

if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل السكربت...")
    asyncio.run(run_daily_task())
    logger.info("🏁 تمت المهمة.")
