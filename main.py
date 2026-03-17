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

DB_NAME = "tech_database.db"
db = sqlite3.connect(DB_NAME)
db.execute("CREATE TABLE IF NOT EXISTS logs (tweet_id TEXT PRIMARY KEY, type TEXT, date TEXT)")
db.commit()

# ================= 🧹 MAINTENANCE =================
def run_maintenance():
    try:
        limit_date = (datetime.now() - timedelta(days=7)).isoformat()
        db.execute("DELETE FROM logs WHERE date < ?", (limit_date,))
        db.commit()
        logger.info(f"🧹 تم تنظيف السجلات القديمة.")
    except Exception as e: logger.error(e)

# ================= 🛡️ FILTERS =================
BLACKLIST = ["يا شباب", "يا جماعة", "لا تقلقوا", "فرصة", "مذهل", "تكنو", "هواوي"]
BAD_REPLY = ["كذاب", "نصاب", "بوت", "غبي", "سيء"]

def clean_pro(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    for word in BLACKLIST: text = text.replace(word, '')
    return " ".join(text.split()).strip()

# ================= 🧠 AI ENGINE =================
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
                        {"role": "system", "content": f"{system}\n- التاريخ: 2026.\n- الأسلوب: تقني سيادي مقتضب."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except: return None

# ================= 🕵️ SMART REPLY (6-Hour Filter) =================
async def smart_reply():
    try:
        me = twitter.get_me(user_auth=True).data
        my_id = str(me.id)
        
        # جلب المنشنات مع تفعيل حقول الوقت
        mentions = twitter.get_users_mentions(
            id=my_id, 
            max_results=15, 
            user_auth=True, 
            tweet_fields=['created_at', 'author_id']
        )
        
        if not mentions or not mentions.data: return

        # تحديد "الخط الزمني الأحمر" (قبل 6 ساعات من الآن)
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=6)

        for tweet in mentions.data:
            tweet_id = str(tweet.id)
            author_id = str(tweet.author_id)
            created_at = tweet.created_at # هذا التاريخ يأتي بصيغة UTC من تويتر

            # 1. فحص الوقت: إذا كانت التغريدة أقدم من 6 ساعات، تجاهلها تماماً
            if created_at < time_threshold:
                logger.info(f"⏳ تجاهل تغريدة قديمة (ID: {tweet_id}) - مضى عليها أكثر من 6 ساعات.")
                continue

            # 2. منع الرد على النفس أو التكرار
            exists = db.execute("SELECT tweet_id FROM logs WHERE tweet_id=?", (tweet_id,)).fetchone()
            if exists or author_id == my_id: continue

            # 3. برومبت الذكاء العميق
            deep_prompt = """أنت CTO تقني في 2026. رد بمعلومة هندسية دقيقة وعميقة.
            - ممنوع الموافقة السطحية.
            - الأسلوب: خليجي مهني مقتضب جداً.
            - إذا كان المنشور تافهاً، أجب بـ 'IGNORE'."""

            answer = await ask_ai(deep_prompt, tweet.text)
            
            if answer and "IGNORE" not in answer.upper():
                twitter.create_tweet(text=clean_pro(answer), in_reply_to_tweet_id=tweet_id, user_auth=True)
                db.execute("INSERT INTO logs VALUES (?, ?, ?)", (tweet_id, "replied", datetime.now().isoformat()))
                db.commit()
                logger.success(f"🧠 رد ذكي وعميق على تغريدة حديثة: {tweet_id}")
            else:
                db.execute("INSERT INTO logs VALUES (?, ?, ?)", (tweet_id, "ignored", datetime.now().isoformat()))
                db.commit()
                
    except Exception as e: logger.error(f"Reply Error: {e}")

# ================= 🧵 FUTURE MISSION =================
async def run_mission():
    logger.info("📡 رصد تقنيات المستقبل...")
    topics = ["معالجات 1nm", "iOS 20", "6G Networks", "GPT-6", "Quantum Mobile"]
    topic = random.choice(topics)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"unique future tech features {topic} 2026",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    content = await ask_ai("أنت CTO في 2026. اكتب ثريد 3 تغريدات دسمة. ابدأ بالزبدة. خليجي مهني.", f"المعرفة:\n{knowledge}")
    if not content: return

    tweets = [clean_pro(t) for t in re.split(r'\d+[./]\s\d+|\n\n', content) if len(t) > 20]
    prev_id = None
    for i, t in enumerate(tweets[:3]):
        try:
            msg = f"{i+1}/3: {t}"
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except: pass
    logger.success(f"✅ تم نشر ثريد: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V2200 Real-Time Sovereign Online | Mode: {mode}")
    if mode == "manual":
        run_maintenance()
        await run_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_maintenance, 'cron', hour=3)
    scheduler.add_job(run_mission, 'cron', hour='9,15,21')
    scheduler.add_job(smart_reply, 'interval', minutes=30)
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
