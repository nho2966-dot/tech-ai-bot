import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

# عميل تويتر الموحد
twitter = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# ================= 🗄️ MEMORY (نظام الذاكرة المتطور) =================
db = sqlite3.connect("tech_sovereign_v400.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, type TEXT, timestamp DATETIME)")
db.commit()

def is_processed(uid):
    return db.execute("SELECT id FROM memory WHERE id=?", (uid,)).fetchone() is not None

def save_memory(uid, mtype="post"):
    db.execute("INSERT INTO memory (id, type, timestamp) VALUES (?, ?, ?)", (uid, mtype, datetime.now()))
    db.commit()

# ================= 🛡️ CLEANER & HUMANIZER (الأنسنة) =================
def humanize_text(text):
    # تنظيف الرموز الغريبة والهلوسة
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    # إزالة الترقيم الجاف (1/, 2:) لتبدو كأنها كتابة يدوية
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    # كلمات الحشو اللي تقتل "الأنسنة"
    forbidden = ["يا شباب", "أهلاً بكم", "في هذا الثريد", "إليك الخطوات"]
    for word in forbidden: text = text.replace(word, "")
    return text.strip()

# ================= 🧠 AI BRAIN (The Tech Specialist) =================
async def ask_ai(system, prompt, temp=0.4):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- اللهجة: خليجية بيضاء (إنسانية وغير جافة).\n- التخصص: خبايا تقنية حقيقية 100%."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🧵 AUTO POST (خبايا حقيقية) =================
async def run_daily_mission():
    logger.info("📡 جاري البحث عن خبيئة تقنية دسمة لنشرها...")
    
    # البحث عن شيء حقيقي ومؤكد في 2026
    search_query = "hidden pro hacks for social media and AI tools march 2026"
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": search_query,
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    sys_prompt = "أنت خبير تقني خليجي. استخرج خبيئة (Hack) حقيقية ومذهلة للأفراد. اكتب ثريد 3-4 تغريدات بأسلوب إنساني مشوق، ابدأ بالزبدة فوراً."
    content = await ask_ai(sys_prompt, f"المعلومات الموثقة:\n{knowledge}")
    
    if not content: return
    tweets = [humanize_text(t) for t in re.split(r'\n\n', content) if len(t) > 15]
    
    prev_id = None
    for i, t in enumerate(tweets[:4]):
        try:
            # الترقيم بأسلوب إنساني (1., 2.) أو بدون
            msg = f"{i+1}. {t}" if i > 0 else t
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except Exception as e: logger.error(e)
    logger.success("✅ تم النشر التلقائي للثريد.")

# ================= 💬 SMART REPLY (الردود المؤنسنة) =================
async def smart_reply():
    try:
        me = twitter.get_me().data.id
        mentions = twitter.get_users_mentions(id=me, max_results=5)
        if not mentions.data: return

        for tweet in mentions.data:
            if is_processed(tweet.id): continue
            
            logger.info(f"📩 جاري الرد على منشن: {tweet.text}")
            reply_sys = "أنت مستشار تقني صديق. رد على هذا المنشن بأسلوب خليجي مهذب ومختصر. إذا سأل عن خبيئة أعطه معلومة حقيقية."
            answer = await ask_ai(reply_sys, tweet.text)
            
            if answer:
                twitter.create_tweet(text=humanize_text(answer), in_reply_to_tweet_id=tweet.id)
                save_memory(tweet.id, "reply")
                await asyncio.sleep(10)
    except Exception as e:
        logger.error(f"Reply Error: {e}")

# ================= 🏁 MAIN LOOP (الأتمتة الكاملة) =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V400 Sovereign Online | Mode: {mode}")
    
    if mode == "manual":
        await run_daily_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    # 1. النشر التلقائي (كل يوم الساعة 10 صباحاً و 6 مساءً)
    scheduler.add_job(run_daily_mission, 'cron', hour='10,18')
    # 2. الردود التلقائية (كل 10 دقائق)
    scheduler.add_job(smart_reply, 'interval', minutes=10)
    
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
