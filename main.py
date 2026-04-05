import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
import random
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

# إعداد اتصال تويتر (مع التأكد من صلاحيات Write)
try:
    twitter = tweepy.Client(
        consumer_key=CONF["X"]["key"],
        consumer_secret=CONF["X"]["secret"],
        access_token=CONF["X"]["token"],
        access_token_secret=CONF["X"]["access_s"],
        wait_on_rate_limit=True
    )
except Exception as e:
    logger.error(f"Twitter Init Error: {e}")

# ================= 🗄️ DATABASE SETUP =================
DB_NAME = "tech_database.db"
db = sqlite3.connect(DB_NAME)
db.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        tweet_id TEXT PRIMARY KEY, 
        author_id TEXT,
        type TEXT, 
        style TEXT, 
        hook TEXT, 
        likes INTEGER DEFAULT 0, 
        retweets INTEGER DEFAULT 0, 
        date TEXT
    )
""")
db.commit()

# ================= 🛡️ FILTERS & UTILS =================
def clean_pro(text):
    text = re.sub(r'[\u4e00-\u9fff]+', '', text) # حذف الصيني
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text) # تنظيف الرموز
    return " ".join(text.split()).strip()[:275]

# ================= 🤖 AI ENGINE (DIAGNOSTIC MODE) =================
async def ask_ai(prompt):
    system = """أنت خبير تقني خليجي في عام 2026. 
    تحدث بلهجة بيضاء واثقة، ركز على حلول الأفراد (Individuals). 
    استخدم مصطلحات تقنية إنجليزية بين قوسين."""
    
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            
            # كشف الخطأ إذا كان من Groq (الرصيد أو المفتاح)
            if res.status_code != 200:
                logger.error(f"❌ Groq API Error ({res.status_code}): {res.text}")
                return None
                
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Connection Error: {e}")
        return None

# ================= 🧵 MISSION (INDEPENDENT) =================
async def run_mission():
    logger.info("📡 بدء مهمة النشر (Independent Mode)...")
    
    topics = [
        "مستقبل الهواتف الذكية في 2026",
        "تطور الـ AI الشخصي (Personal AI)",
        "كيف تحمي بصمتك الرقمية اليوم؟",
        "تطبيقات الـ Blockchain للأفراد في الخليج"
    ]
    
    content = await ask_ai(f"اكتب ثريد من تغريدتين عن {random.choice(topics)} لعام 2026.")
    
    if not content:
        logger.error("❌ فشل الحصول على محتوى من AI.")
        return

    try:
        # محاولة النشر في X
        tweets = [t.strip() for t in content.split('\n\n') if len(t.strip()) > 10]
        p_id = None
        for i, t in enumerate(tweets[:2]):
            msg = clean_pro(t)
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=p_id, user_auth=True)
            p_id = res.data["id"]
            logger.success(f"✅ تم نشر التغريدة {i+1}")
            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"❌ Twitter Posting Error: {e}")

# ================= 🕵️ SMART REPLY =================
async def smart_reply():
    logger.info("🕵️ فحص المنشنات...")
    try:
        me = twitter.get_me(user_auth=True).data
        mentions = twitter.get_users_mentions(id=me.id, max_results=5, user_auth=True)
        
        if not mentions or not mentions.data:
            logger.info("⏳ لا توجد منشنات.")
            return

        for tweet in mentions.data:
            # تجنب الرد المتكرر
            if db.execute("SELECT tweet_id FROM logs WHERE author_id=?", (str(tweet.author_id),)).fetchone():
                continue
                
            ans = await ask_ai(f"رد باختصار خليجي تقني على: {tweet.text}")
            if ans:
                final = clean_pro(ans)
                twitter.create_tweet(text=final, in_reply_to_tweet_id=tweet.id, user_auth=True)
                db.execute("INSERT INTO logs (tweet_id, author_id, date) VALUES (?, ?, ?)", 
                           (str(tweet.id), str(tweet.author_id), datetime.now().isoformat()))
                db.commit()
                logger.success(f"🎯 تم الرد على {tweet.author_id}")
    except Exception as e:
        logger.error(f"Reply Loop Error: {e}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 Sniper Engine Online | Mode: {mode}")
    
    if mode == "manual":
        await run_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_mission, 'cron', hour='9,21')
    scheduler.add_job(smart_reply, 'interval', minutes=30)
    scheduler.start()
    
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    asyncio.run(main_loop(mode))
