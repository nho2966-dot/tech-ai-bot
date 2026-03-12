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

# إعداد تويتر
twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ MEMORY DB =================
db = sqlite3.connect("tech_bot.db")
db.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY)")
db.commit()

def is_processed(uid):
    return db.execute("SELECT id FROM processed WHERE id=?", (uid,)).fetchone() is not None

def save_processed(uid):
    db.execute("INSERT INTO processed (id) VALUES (?)", (uid,))
    db.commit()

# ================= 🛡️ TEXT CLEANER =================
def clean_text(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:()@#/-]', '', text)
    boring = ["أهلاً بكم", "في هذا الثريد", "هل تعلم", "تخيل"]
    for s in boring: text = text.replace(s, "")
    return " ".join(text.split()).strip()

# ================= 🧠 AI ENGINE =================
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
                        {"role": "system", "content": system + "\nاللهجة: خليجية تقنية حادة."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 📹 VIDEO INTEL =================
async def analyze_video(url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return f"Title: {info.get('title')}\nDescription: {info.get('description')[:500]}"
    except: return None

# ================= 🧵 DAILY THREAD MISSION =================
async def daily_mission():
    logger.info("🎯 تبدأ المهمة اليومية: اكتشاف ونشر...")
    topic_sys = "أنت محلل استخبارات تقنية. اقترح ترند AI Agent أو LLM Architecture دسم."
    topic = await ask_ai(topic_sys, "أعطني عنواناً تقنياً صادماً.", 0.7)
    
    if not topic: return

    # بحث وتحليل
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": topic, "search_depth": "advanced"})
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    thread_sys = "أنت Senior Architect. اكتب ثريد من 5 تغريدات. ابدأ بالـ Architecture. اذكر أدوات محددة."
    raw_thread = await ask_ai(thread_sys, f"الموضوع: {topic}\nالمعرفة: {knowledge}", 0.5)
    
    tweets = [clean_text(t) for t in re.split(r'\d+\s*[/-]\s*', raw_thread) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:5]):
        text = f"{i+1}/ {t}"
        res = twitter.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
        prev_id = res.data["id"]
        await asyncio.sleep(5)
    logger.success("🔥 تم نشر الثريد بنجاح!")

# ================= 🤖 SMART REPLY =================
async def check_mentions():
    logger.info("🔍 فحص الردود والمنشن...")
    try:
        me = twitter.get_me().data.id
        mentions = twitter.get_users_mentions(id=me)
        if not mentions.data: return

        for tweet in mentions.data:
            if is_processed(f"reply_{tweet.id}"): continue
            
            # هل هو رابط فيديو؟
            url_match = re.search(r'(https?://\S+)', tweet.text)
            if url_match and "youtu" in url_match.group(0):
                intel = await analyze_video(url_match.group(0))
                reply_sys = "أنت خبير تقني تلخص فيديوهات يوتيوب بذكاء."
                answer = await ask_ai(reply_sys, f"لخص هذا الفيديو بـ 200 حرف: {intel}")
            else:
                reply_sys = "أنت Senior Architect. رد بذكاء وعمق تقني."
                answer = await ask_ai(reply_sys, f"سؤال المتابع: {tweet.text}")

            if answer:
                twitter.create_tweet(text=clean_text(answer), in_reply_to_tweet_id=tweet.id)
                save_processed(f"reply_{tweet.id}")
                logger.success("✅ تم الرد.")
    except Exception as e: logger.error(e)

# ================= 🚀 SCHEDULER & MAIN =================
scheduler = AsyncIOScheduler()

async def main_loop():
    logger.info("🚀 AI Media Engine V125 ONLINE")
    
    # جدولة المهام داخل الـ Loop
    scheduler.add_job(daily_mission, 'cron', hour=10) # 10 صباحاً
    scheduler.add_job(check_mentions, 'interval', minutes=15) # كل ربع ساعة
    
    scheduler.start()
    logger.info("📅 Scheduler started successfully.")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except Exception as e:
        logger.critical(f"Fatal Startup Error: {e}")
