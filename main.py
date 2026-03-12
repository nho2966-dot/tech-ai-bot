import os
import re
import asyncio
import httpx
import tweepy
import sqlite3
import numpy as np
import yt_dlp
from loguru import logger
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG =================
# تأكد أنك وضعت كل المفاتيح في Secrets الـ GitHub
twitter = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

# ================= 📹 VIDEO INTEL (yt-dlp) =================
async def analyze_video(url):
    logger.info(f"🎥 جاري سحب وتحليل الفيديو: {url}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'skip_download': True,
        'writeinfojson': True,
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # نأخذ الوصف والعنوان والترجمة إن وجدت
            description = info.get('description', '')
            title = info.get('title', '')
            return f"Title: {title}\nDescription: {description}"
    except Exception as e:
        logger.error(f"Video Error: {e}")
        return None

# ================= 🧠 AI BRAIN (Expert Prompting) =================
async def ask_ai(system, prompt, temp=0.6):
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": temp,
                "messages": [{"role": "system", "content": system + "\nاللهجة: خليجية تقنية حادة."}, 
                             {"role": "user", "content": prompt}]
            }
        )
        return res.json()["choices"][0]["message"]["content"]

# ================= 🧵 MULTI-SOURCE THREAD =================
async def create_video_thread(video_url):
    raw_data = await analyze_video(video_url)
    if not raw_data: return
    
    sys = "أنت Senior AI Architect. حلل محتوى هذا الفيديو واستخرج 'الخلاصة التقنية' للأفراد."
    knowledge = await ask_ai(sys, raw_data)
    
    # تحويل الخلاصة لثريد
    thread_sys = "اكتب ثريد تويتر من 5 تغريدات تقنية عميقة. ابدأ بالـ Impact. اذكر الأدوات."
    thread_raw = await ask_ai(thread_sys, knowledge, 0.4)
    
    # تنظيف ونشر (نفس ميكانيكية الـ V120)
    tweets = [t.strip() for t in re.split(r'\d+\s*[/-]\s*', thread_raw) if len(t) > 20]
    # (كود النشر هنا...)

# ================= 🤖 SMART REPLY (With Context) =================
async def smart_reply():
    logger.info("🔍 فحص المنشن للردود الذكية...")
    me = twitter.get_me()
    mentions = twitter.get_users_mentions(id=me.data.id)
    if not mentions.data: return

    for tweet in mentions.data:
        # إذا المنشن فيه رابط يوتيوب، حلله فوراً ورد عليه
        url_match = re.search(r'(https?://\S+)', tweet.text)
        if url_match and "youtube" in url_match.group(0):
            video_summary = await analyze_video(url_match.group(0))
            reply = await ask_ai("أنت خبير تقني تلخص الفيديوهات.", f"لخص هذا بذكاء: {video_summary}")
            twitter.create_tweet(text=f"زبدة الفيديو: {reply[:250]}", in_reply_to_tweet_id=tweet.id)
        else:
            # رد تقني عادي (كما في V120)
            pass

# ================= 🚀 SCHEDULER =================
scheduler = AsyncIOScheduler()
# مهمة الصباح: تحليل ترند يوتيوب ونشر ثريد
scheduler.add_job(create_video_thread, 'cron', hour=9, args=["https://www.youtube.com/@ThePyCoach/videos"]) # مثال لقناة تقنية
# مهمة المساء: الردود الذكية
scheduler.add_job(smart_reply, 'interval', minutes=30)
scheduler.start()

async def main():
    logger.info("🚀 AI Media Engine V125 (Video Edition) is Active!")
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
