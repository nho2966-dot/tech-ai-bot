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

# ================= 🏷️ قاموس المنشن الذكي =================
MENTIONS_MAP = {
    "أبل": "@Apple", "آيفون": "@Apple", "iOS": "@Apple",
    "تسلا": "@Tesla", "إيلون ماسك": "@elonmusk",
    "مايكروسوفت": "@Microsoft", "ويندوز": "@Windows", "Azure": "@Azure",
    "قوقل": "@Google", "أندرويد": "@Android",
    "سامسونج": "@Samsung", "سبيس إكس": "@SpaceX",
    "أنفيديا": "@nvidia", "أوبن إيه آي": "@OpenAI", "ChatGPT": "@OpenAI"
}

# ================= 🛡️ FILTERS =================
BLACKLIST = ["يا شباب", "يا جماعة", "لا تقلقوا", "فرصة", "مذهل", "نصيحة", "أنصحك", "يجب عليك"]

def clean_pro(text):
    text = re.sub(r'^\d+[/]\d+[:/-]*\s*', '', text) 
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    for word in BLACKLIST: text = text.replace(word, '')
    
    # إضافة المنشن الذكي داخل النص
    for key, mention in MENTIONS_MAP.items():
        if key in text and mention not in text:
            text = text.replace(key, f"{key} ({mention})", 1)
            
    return " ".join(text.split()).strip()

# ================= 🧠 AI ENGINE (Smooth & Smart) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.8,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- التاريخ: 2026.\n- الأسلوب: تقني سلس ومتحمس (سوالف زملاء)."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except: return None

# ================= 🕵️ SMART REPLY (6h Filter) =================
async def smart_reply():
    try:
        me = twitter.get_me(user_auth=True).data
        my_id = str(me.id)
        mentions = twitter.get_users_mentions(id=my_id, max_results=10, user_auth=True, tweet_fields=['created_at', 'author_id'])
        if not mentions or not mentions.data: return

        time_threshold = datetime.now(timezone.utc) - timedelta(hours=6)

        for tweet in mentions.data:
            tweet_id = str(tweet.id)
            if tweet.created_at < time_threshold: continue
            exists = db.execute("SELECT tweet_id FROM logs WHERE tweet_id=?", (tweet_id,)).fetchone()
            if exists or str(tweet.author_id) == my_id: continue

            ans = await ask_ai("أنت زميل تقني في 2026. رد بسلاسة وذكاء بدون رسميات.", tweet.text)
            if ans and "IGNORE" not in ans.upper():
                twitter.create_tweet(text=clean_pro(ans), in_reply_to_tweet_id=tweet_id, user_auth=True)
                db.execute("INSERT INTO logs VALUES (?, ?, ?)", (tweet_id, "replied", datetime.now().isoformat()))
                db.commit()
    except Exception as e: logger.error(e)

# ================= 🧵 MISSION (Media + Smart Tags) =================
async def run_mission():
    logger.info("📡 استكشاف 2026 (وسائط + منشن ذكي)...")
    topics = ["معالجات Azure Maya 200", "روبوتات Helix 02", "نظارات الواقع المعزز أبل", "مستقبل SpaceX 2026"]
    topic = random.choice(topics)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"detailed visual media and news {topic} 2026",
            "search_depth": "advanced",
            "include_images": True
        })
        results = r.json()
        knowledge = "\n".join([x['content'] for x in results.get("results", [])])
        media_url = results["images"][0] if results.get("images") else ""

    content = await ask_ai("أنت مهتم بالتقنية في 2026. اكتب ثريد 3 تغريدات سوالف ممتعة.", f"المعرفة:\n{knowledge}")
    if not content: return

    raw_tweets = [t for t in re.split(r'\n\n|\d+[./]\s', content) if len(t) > 30]
    prev_id = None
    for i, t in enumerate(raw_tweets[:3]):
        try:
            msg = f"{i+1}/3: {clean_pro(t)}"
            if i == 0 and media_url: msg += f"\n\n📷 {media_url}"
            
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except: pass
    logger.success(f"✅ تم نشر الثريد: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V2800 Strategic Online | Mode: {mode}")
    if mode == "manual":
        await run_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_mission, 'cron', hour='9,15,21')
    scheduler.add_job(smart_reply, 'interval', minutes=30)
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
