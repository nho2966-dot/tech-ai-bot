import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
import numpy as np
import yt_dlp
from loguru import logger
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# شحن الإعدادات
load_dotenv()

# ================= 🔐 CONFIGURATION =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

# إعداد تويتر V2
twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ MEMORY DB =================
db = sqlite3.connect("tech_empire_v130.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY)")
db.commit()

def is_seen(uid):
    return db.execute("SELECT id FROM memory WHERE id=?", (uid,)).fetchone() is not None

def save_seen(uid):
    db.execute("INSERT INTO memory (id) VALUES (?)", (uid,))
    db.commit()

# ================= 🛡️ TEXT CLEANER =================
def clean_text(text):
    # تنظيف الحروف والرموز غير المرغوبة
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:()@#/-]', '', text)
    boring = ["أهلاً بكم", "في هذا الثريد", "هل تعلم", "تخيل", "إليك الخطوات"]
    for s in boring: text = text.replace(s, "")
    return " ".join(text.split()).strip()

# ================= 🧠 AI ENGINE (Expert Mode) =================
async def ask_ai(system, prompt, temp=0.6):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- اللهجة: خليجية تقنية بيضاء.\n- الشخصية: CTO خبير."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 📹 VIDEO INTEL (yt-dlp) =================
async def analyze_video(url):
    logger.info(f"🎥 تحليل فيديو يوتيوب: {url}")
    ydl_opts = {'quiet': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return f"Title: {info.get('title')}\nDescription: {info.get('description')[:500]}"
    except Exception as e:
        logger.error(f"Video Error: {e}")
        return "فشل تحليل الفيديو تقنياً."

# ================= 🧵 CORE MISSION (The Thread) =================
async def run_daily_mission(custom_topic=None):
    logger.info("🎯 جاري تنفيذ المهمة (نشر ثريد)...")
    
    # 1. تحديد الموضوع (تلقائي أو يدوي)
    if custom_topic:
        topic = custom_topic
    else:
        topic_sys = "اقترح ترند تقني عميق (AI Agents, RAG, Web3) موجه للأفراد."
        topic = await ask_ai(topic_sys, "أعطني عنواناً داسماً بالخليجي.", 0.8)

    if not topic: return

    # 2. بحث Tavily
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": topic, "search_depth": "advanced"})
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    # 3. توليد الثريد
    thread_sys = "أنت Senior Solution Architect. اكتب ثريد من 5 تغريدات. ادخل في الـ Architecture والأدوات فوراً."
    raw_thread = await ask_ai(thread_sys, f"الموضوع: {topic}\nالمعرفة: {knowledge}", 0.5)
    
    tweets = [clean_text(t) for t in re.split(r'\d+\s*[/-]\s*', raw_thread) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:5]):
        full_tweet = f"{i+1}/ {t}"
        res = twitter.create_tweet(text=full_tweet, in_reply_to_tweet_id=prev_id)
        prev_id = res.data["id"]
        await asyncio.sleep(5)
    
    logger.success(f"🔥 تم نشر الثريد بنجاح عن: {topic}")

# ================= 🤖 SMART REPLY & REMOTE CONTROL =================
async def check_mentions():
    logger.info("🔍 فحص المنشن والردود...")
    try:
        me = twitter.get_me().data.id
        mentions = twitter.get_users_mentions(id=me)
        if not mentions.data: return

        for tweet in mentions.data:
            if is_seen(f"reply_{tweet.id}"): continue
            
            # ميزة التحكم عن بُعد: إذا المنشن يحتوي على "اكتب ثريد عن"
            if "اكتب ثريد عن" in tweet.text:
                requested_topic = tweet.text.split("اكتب ثريد عن")[1].strip()
                logger.info(f"📝 طلب يدوي مكتشف: {requested_topic}")
                await run_daily_mission(custom_topic=requested_topic)
                save_seen(f"reply_{tweet.id}")
                continue

            # الرد العادي أو تحليل يوتيوب
            url_match = re.search(r'(https?://\S+)', tweet.text)
            if url_match and "youtu" in url_match.group(0):
                intel = await analyze_video(url_match.group(0))
                answer = await ask_ai("أنت خبير تقني تلخص فيديوهات.", f"لخص بذكاء هندسي: {intel}")
            else:
                answer = await ask_ai("أنت خبير تقني رصين.", f"رد على استفسار المتابع: {tweet.text}")

            if answer:
                twitter.create_tweet(text=clean_text(answer), in_reply_to_tweet_id=tweet.id)
                save_seen(f"reply_{tweet.id}")
                logger.success("✅ تم الرد بنجاح.")
    except Exception as e:
        logger.error(f"Reply Error: {e}")

# ================= 🚀 MAIN ENTRY POINT =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 AI Media Engine V130 Started | Mode: {mode}")

    if mode == "manual":
        # نشر فوري ثم الخروج (مثالي للـ GitHub Actions اليدوي)
        await run_daily_mission()
        return

    # وضع الجدولة المستمرة
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_mission, 'cron', hour=10) # 10 صباحاً
    scheduler.add_job(check_mentions, 'interval', minutes=15)
    
    scheduler.start()
    logger.info("📅 Scheduler Active.")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    # فحص الأوامر: python main.py manual للنشر الفوري
    run_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    
    try:
        asyncio.run(main_loop(mode=run_mode))
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
