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
db = sqlite3.connect("tech_sovereignty_v150.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY)")
db.commit()

def is_seen(uid):
    return db.execute("SELECT id FROM memory WHERE id=?", (uid,)).fetchone() is not None

def save_seen(uid):
    db.execute("INSERT INTO memory (id) VALUES (?)", (uid,))
    db.commit()

# ================= 🛡️ ADVANCED CLEANER =================
def clean_text(text):
    # تنظيف الحروف والرموز غير المرغوبة ومنع الهلوسة اللغوية
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:()@#/-]', '', text)
    # حذف الافتتاحيات الضعيفة
    weak_starts = ["مرحباً يا شباب", "في هذا المنشور", "هل تعلم", "اليوم سأشارككم", "أهلاً بكم"]
    for s in weak_starts: text = text.replace(s, "")
    return " ".join(text.split()).strip()

# ================= 🧠 AI ENGINE (CTO MODE) =================
async def ask_ai(system, prompt, temp=0.4): # تقليل الـ Temp لزيادة الدقة التقنية
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- اللهجة: خليجية تقنية بيضاء رصينة.\n- الشخصية: Senior Solution Architect."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 📹 VIDEO INTEL (Deep Analysis) =================
async def analyze_video(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return f"Title: {info.get('title')}\nDescription: {info.get('description')}"
    except Exception as e:
        logger.error(f"Video Error: {e}")
        return "تحليل الفيديو فشل."

# ================= 🧵 CORE MISSION (Technical Threads) =================
async def run_daily_mission(custom_topic=None):
    logger.info("🎯 جاري استخراج "الزبدة الهندسية" ونشر الثريد...")
    
    # 1. تحديد الموضوع (Technical Focus)
    if custom_topic:
        topic = custom_topic
    else:
        topic_sys = "اقترح ترند AI Architecture معقد (مثل: Multi-agent Orchestration أو RAG Optimization) يهم المطورين."
        topic = await ask_ai(topic_sys, "أعطني عنواناً تقنياً داسماً.", 0.7)

    if not topic: return

    # 2. بحث Tavily (Deep Search)
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": topic, "search_depth": "advanced"})
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    # 3. توليد الثريد (High-Density Architecture)
    thread_sys = """أنت CTO متمرد وخبير نظم. 
    قواعد النشر الصارمة:
    - ابدأ بـ Hook تقني صادم (Problem/Solution).
    - اذكر الـ Workflow والـ Tech Stack (أدوات مثل: LangChain, Qdrant, FastAPI).
    - استخدم مصطلحات: Latency, Scalability, Vectors, Inference.
    - ممنوع المقدمات (مرحباً، إليكم). ادخل في الـ Architecture فوراً."""
    
    raw_thread = await ask_ai(thread_sys, f"الموضوع: {topic}\nالمعرفة: {knowledge}", 0.4)
    
    tweets = [clean_text(t) for t in re.split(r'\d+\s*[/-]\s*', raw_thread) if len(t) > 30]
    
    prev_id = None
    for i, t in enumerate(tweets[:6]): # زيادة العمق لـ 6 تغريدات
        full_tweet = f"{i+1}/ {t}"
        res = twitter.create_tweet(text=full_tweet, in_reply_to_tweet_id=prev_id)
        prev_id = res.data["id"]
        await asyncio.sleep(5)
    
    logger.success(f"🔥 تم نشر المحتوى السيادي عن: {topic}")

# ================= 🤖 SMART REPLY (Expert Context) =================
async def check_mentions():
    logger.info("🔍 فحص المنشن للردود الاستشارية...")
    try:
        me = twitter.get_me().data.id
        mentions = twitter.get_users_mentions(id=me)
        if not mentions.data: return

        for tweet in mentions.data:
            if is_seen(f"reply_{tweet.id}"): continue
            
            # ميزة التحكم عن بُعد (Remote Trigger)
            if "اكتب ثريد عن" in tweet.text:
                requested_topic = tweet.text.split("اكتب ثريد عن")[1].strip()
                await run_daily_mission(custom_topic=requested_topic)
                save_seen(f"reply_{tweet.id}")
                continue

            # الرد الهندسي
            url_match = re.search(r'(https?://\S+)', tweet.text)
            if url_match and "youtu" in url_match.group(0):
                intel = await analyze_video(url_match.group(0))
                answer = await ask_ai("أنت خبير تقني يحلل الـ Architecture.", f"لخص هندسة الفيديو بذكاء: {intel}")
            else:
                answer = await ask_ai("أنت Senior Architect.", f"رد على هذا السؤال التقني بعمق: {tweet.text}")

            if answer:
                twitter.create_tweet(text=clean_text(answer), in_reply_to_tweet_id=tweet.id)
                save_seen(f"reply_{tweet.id}")
                logger.success("✅ تم تقديم الاستشارة التقنية.")
    except Exception as e:
        logger.error(f"Reply Error: {e}")

# ================= 🚀 EXECUTION =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 AI Media Engine V150 (CTO Edition) | Mode: {mode}")

    if mode == "manual":
        await run_daily_mission()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_mission, 'cron', hour=10)
    scheduler.add_job(check_mentions, 'interval', minutes=15)
    
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    run_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    try:
        asyncio.run(main_loop(mode=run_mode))
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
