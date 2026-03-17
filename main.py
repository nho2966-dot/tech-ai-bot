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
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# قاعدة بيانات بذاكرة "متجددة"
DB_NAME = "tech_sovereignty_v1700.db"
db = sqlite3.connect(DB_NAME)
db.execute("CREATE TABLE IF NOT EXISTS logs (tweet_id TEXT PRIMARY KEY, type TEXT, date TIMESTAMP)")
db.commit()

# ================= 🧹 خاصية التنظيف الذاتي (Maintenance) =================
def run_maintenance():
    """مسح السجلات القديمة للحفاظ على خفة القاعدة ومنع امتلائها"""
    try:
        limit_date = (datetime.now() - timedelta(days=7)).isoformat()
        cursor = db.cursor()
        cursor.execute("DELETE FROM logs WHERE date < ?", (limit_date,))
        db.commit()
        logger.info(f"🧹 تمت صيانة قاعدة البيانات وحذف السجلات الأقدم من: {limit_date}")
    except Exception as e:
        logger.error(f"Maintenance Error: {e}")

# ================= 🛡️ الفلاتر =================
BLACKLIST_WORDS = ["يا شباب", "يا جماعة", "لا تقلقوا", "فرصة", "مذهل", "تكنو", "هواوي"]
BAD_REPLY_WORDS = ["كذاب", "بايخ", "سيء", "حمار", "غبي", "كلب", "نصاب", "بوت"]

def clean_pro(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    for word in BLACKLIST_WORDS:
        text = text.replace(word, '')
    return " ".join(text.split()).strip()

# ================= 🧠 محرك ذكاء المستقبل =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- التاريخ: 2026.\n- الأسلوب: رصين."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except: return None

# ================= 🕵️ رادار الردود (Anti-Loop) =================
async def smart_reply():
    try:
        me = twitter.get_me().data
        my_id = str(me.id)
        
        mentions = twitter.get_users_mentions(id=my_id, max_results=10)
        if not mentions or not mentions.data: return

        for tweet in mentions.data:
            tweet_id = str(tweet.id)
            author_id = str(tweet.author_id) if hasattr(tweet, 'author_id') else ""
            
            # شرط عدم التكرار وعدم الرد على النفس
            exists = db.execute("SELECT tweet_id FROM logs WHERE tweet_id=?", (tweet_id,)).fetchone()
            if exists or author_id == my_id: continue
            
            if any(bad in tweet.text.lower() for bad in BAD_REPLY_WORDS):
                db.execute("INSERT INTO logs VALUES (?, ?, ?)", (tweet_id, "ignored", datetime.now().isoformat()))
                db.commit()
                continue

            answer = await ask_ai("أنت خبير تقني في 2026. رد باختصار شديد.", tweet.text)
            if answer:
                twitter.create_tweet(text=clean_pro(answer), in_reply_to_tweet_id=tweet_id)
                db.execute("INSERT INTO logs VALUES (?, ?, ?)", (tweet_id, "replied", datetime.now().isoformat()))
                db.commit()
                logger.success(f"✅ رد ذكي على: {tweet_id}")
                
    except Exception as e: logger.error(f"Reply Error: {e}")

# ================= 🧵 المهمة الدورية =================
async def run_future_mission():
    logger.info("📡 رصد تقنيات 2026 وما فوق...")
    
    future_topics = [
        "معالجات 1nm القادمة", "نظام iOS 20", "شبكات 6G", "GPT-6 Agents", "الواقع المعزز 2026"
    ]
    topic = random.choice(future_topics)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"latest tech features {topic} 2026",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    content = await ask_ai("أنت CTO في 2026. اكتب ثريد 3 تغريدات. ابدأ بالزبدة. خليجي مهني.", f"المعرفة:\n{knowledge}")
    if not content: return

    tweets = [clean_pro(t) for t in re.split(r'\d+[./]\s\d+|\n\n', content) if len(t) > 20]
    prev_id = None
    for i, t in enumerate(tweets[:3]):
        try:
            msg = f"{i+1}/3: {t}"
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except: pass

    logger.success(f"✅ تم نشر الثريد: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V1700 Self-Maintainer Online | Mode: {mode}")
    if mode == "manual":
        run_maintenance() # تشغيل التنظيف يدوياً عند التجربة
        await run_future_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    # تنظيف القاعدة يومياً الساعة 3 فجراً
    scheduler.add_job(run_maintenance, 'cron', hour=3)
    # نشر الثريد 3 مرات يومياً
    scheduler.add_job(run_future_mission, 'cron', hour='9,15,21')
    # فحص المنشنات كل 30 دقيقة
    scheduler.add_job(smart_reply, 'interval', minutes=30)
    
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
