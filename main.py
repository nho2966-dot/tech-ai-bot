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
import schedule

# =========================================================
# 🔐 KEYS & AUTH
# =========================================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
XAI_KEY = os.getenv("XAI_API_KEY")        # Grok
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
# ⚙️ CONFIGURABLE PARAMETERS
# =========================================================
daily_videos_count = 2           # عدد الفيديوهات اليومية
video_length_seconds = 45        # مدة الفيديو بالثواني
tweets_per_thread = 3            # عدد التغريدات لكل سلسلة

# =========================================================
# 🛡 IMPROVED FILTER
# =========================================================
def nasser_filter(text):
    if not text: return ""
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    
    # قائمة الكلمات الممنوعة
    banned = [
        "stock","market","investment","funding","revenue","profit","سهم","تداول","عملة","cryptocurrency","بيتكوين"
    ]
    for word in banned: 
        text = re.sub(rf"\b{word}\b", "", text, flags=re.IGNORECASE)
        
    return text.strip()

# =========================================================
# 🧠 SOVEREIGN BRAIN
# =========================================================
class SovereignBrain:
    async def generate(self, prompt, system_msg):
        brains = [
            ("GROK", "https://api.x.ai/v1/chat/completions", {"Authorization": f"Bearer {XAI_KEY}"}, "grok-beta"),
            ("OPENAI", "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {OPENAI_KEY}"}, "gpt-4o-mini"),
            ("QWEN", "https://api.labs.qwen.ai/v1/chat/completions", {"Authorization": f"Bearer {QWEN_KEY}"}, "qwen-7b")
        ]
        for name, url, headers, model in brains:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    r = await client.post(url, headers=headers, json={
                        "model": model,
                        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
                    })
                    r.raise_for_status()
                    return r.json()['choices'][0]['message']['content']
            except Exception as e:
                logger.warning(f"⚠️ Brain {name} failed: {e}")
                continue
        return "سر تقني جديد في الطريق إليكم.."

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
    logger.info("🔎 البحث عن خبايا تقنية جديدة لم تُنشر من قبل...")
    # البحث في الفيديوهات المنشورة خلال اليومين الماضيين
    ydl_opts = {'quiet': True, 'extract_flat': True, 'daterange': yt_dlp.utils.DateRange('now-2days','now')}
    random.shuffle(TRUSTED_CHANNELS)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for channel in TRUSTED_CHANNELS:
            try:
                res = ydl.extract_info(channel, download=False)
                if 'entries' in res and res['entries']:
                    # المرور على أول 5 فيديوهات بدلاً من الأول فقط
                    for video in res['entries'][:5]:
                        title = video.get('title','')
                        v_url = video.get('url')
                        
                        # تخطي الفيديوهات التي تحتوي على كلمات ممنوعة في العنوان
                        if any(w in title.lower() for w in ["stock","market","earnings"]):
                            continue
                            
                        # التحقق من قاعدة البيانات
                        v_hash = hashlib.sha256(title.encode()).hexdigest()
                        cursor.execute("SELECT hash FROM published WHERE hash=?", (v_hash,))
                        if cursor.fetchone():
                            continue # الفيديو تم نشره، نبحث عن الذي يليه
                            
                        return {"title": title, "url": v_url, "hash": v_hash}
            except Exception as e:
                logger.warning(f"⚠️ فشل الجلب من {channel}: {e}")
                continue
    return None

# =========================================================
# 🎬 VIDEO PROCESSING
# =========================================================
def process_video(url):
    logger.info("🎬 تحميل ومعالجة الفيديو...")
    output_raw = "raw_vid.mp4"
    output_final = "nasser_vid.mp4"
    
    ydl_opts = {'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', 'outtmpl': output_raw, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    
    cmd = [
        "ffmpeg", "-y", "-i", output_raw, "-t", str(video_length_seconds),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-c:a", "aac", output_final
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_final

# =========================================================
# 🐦 THREAD POSTING
# =========================================================
async def post_nasser_thread(title, video_path):
    prompt = f"حول هذا الموضوع التقني إلى سلسلة تغريدات (Thread) خليجية عن الخبايا: {title}. قسمها لـ {tweets_per_thread} تغريدات."
    system = "أنت ناصر، خبير خبايا الأجهزة وأسرار الإنترنت والذكاء الاصطناعي."
    raw_content = await brain.generate(prompt, system)
    tweets = [nasser_filter(t) for t in raw_content.split('\n\n') if t][:tweets_per_thread]
    
    logger.info("🐦 رفع الفيديو والتغريدة الأولى...")
    # استخدام chunked=True لضمان رفع الفيديوهات دون مشاكل
    media = api_v1.media_upload(video_path, media_category='tweet_video', chunked=True)
    
    # انتظار المعالجة الذكي على سيرفرات X
    for _ in range(15):
        try:
            status = api_v1.get_media_upload_status(media.media_id)
            if status.processing_info.get("state") == "succeeded":
                break
        except: pass
        logger.info("⏳ الفيديو قيد المعالجة على X...")
        time.sleep(5)
    
    first_tweet = client_v2.create_tweet(text=tweets[0], media_ids=[media.media_id])
    last_id = first_tweet.data['id']
    
    for i in range(1, len(tweets)):
        reply = client_v2.create_tweet(text=tweets[i], in_reply_to_tweet_id=last_id)
        last_id = reply.data['id']
    
    logger.success("✅ تم نشر السلسلة التقنية بنجاح!")

# =========================================================
# 🔄 DAILY FLEXIBLE EXECUTION
# =========================================================
async def run_daily_task():
    for _ in range(daily_videos_count):
        video_data = fetch_tech_video()
        if not video_data: 
            logger.info("⚠️ لا توجد فيديوهات جديدة غير منشورة اليوم.")
            return

        v_hash = video_data['hash']

        try:
            final_vid = process_video(video_data['url'])
            await post_nasser_thread(video_data['title'], final_vid)
            
            cursor.execute("INSERT INTO published VALUES (?,?)", (v_hash, datetime.utcnow().isoformat()))
            conn.commit()
            
            for f in ["raw_vid.mp4", "nasser_vid.mp4"]:
                if os.path.exists(f): os.remove(f)
        except Exception as e:
            logger.error(f"❌ حدث خطأ أثناء المعالجة أو النشر: {e}")

def schedule_daily(hour=10, minute=0):
    schedule.clear()
    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(lambda: asyncio.run(run_daily_task()))
    logger.info(f"🕒 تم جدولة المهمة اليومية الساعة {hour:02d}:{minute:02d}")
    
    while True:
        schedule.run_pending()
        time.sleep(30)

# =========================================================
# 🚀 START FLEXIBLE DAILY SCHEDULER
# =========================================================
if __name__ == "__main__":
    # ضبط الوقت اليومي (مثلاً الساعة 10:00 صباحًا)
    schedule_daily(hour=10, minute=0)
