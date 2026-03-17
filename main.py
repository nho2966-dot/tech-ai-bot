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

# ================= 🛡️ FILTERS & CLEANING =================
BLACKLIST = ["يا شباب", "يا جماعة", "لا تقلقوا", "فرصة", "مذهل", "تكنو", "نصيحة", "أنصحك", "يجب عليك"]

def clean_pro(text):
    # إزالة الترقيم الذاتي الذي قد يولده الـ AI
    text = re.sub(r'^\d+[/]\d+[:/-]*\s*', '', text) 
    # إزالة الحروف غير العربية/الإنجليزية (مثل الصينية)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    for word in BLACKLIST:
        text = text.replace(word, '')
    return " ".join(text.split()).strip()

# ================= 🧠 AI ENGINE (Humanized & Smooth) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.8, # حرارة أعلى قليلاً لإعطاء نصوص أكثر سلاسة وأقل رتابة
                    "messages": [
                        {"role": "system", "content": f"""
                        {system}
                        - نحن في مارس 2026.
                        - الأسلوب: تقني، سلس، وبسيط (تحدث كزميل خبير وليس كمعلم أو مجرب).
                        - ابتعد عن لغة المواعظ (مثل 'يجب' أو 'عليك').
                        - كن منبهراً ومتحمساً كأنك تشارك خبراً مثيراً مع أصدقائك.
                        - ممنوع كتابة الترقيم (1/3) داخل النص.
                        """},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🕵️ SMART REPLY (Recent & Deep) =================
async def smart_reply():
    try:
        me = twitter.get_me(user_auth=True).data
        my_id = str(me.id)
        
        mentions = twitter.get_users_mentions(
            id=my_id, 
            max_results=10, 
            user_auth=True, 
            tweet_fields=['created_at', 'author_id']
        )
        if not mentions or not mentions.data: return

        # تجاهل أي منشن مضى عليه أكثر من 6 ساعات
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=6)

        for tweet in mentions.data:
            tweet_id = str(tweet.id)
            if tweet.created_at < time_threshold: continue
            
            exists = db.execute("SELECT tweet_id FROM logs WHERE tweet_id=?", (tweet_id,)).fetchone()
            if exists or str(tweet.author_id) == my_id: continue

            # برومبت الرد السلس
            reply_prompt = "أنت مهتم بالتقنية وتعيش في 2026. رد على هذا المنشن بسوالف تقنية ذكية وسلسة جداً. جملة واحدة فقط."
            ans = await ask_ai(reply_prompt, tweet.text)
            
            if ans and "IGNORE" not in ans.upper():
                twitter.create_tweet(text=clean_pro(ans), in_reply_to_tweet_id=tweet_id, user_auth=True)
                db.execute("INSERT INTO logs VALUES (?, ?, ?)", (tweet_id, "replied", datetime.now().isoformat()))
                db.commit()
                logger.success(f"🧠 رد سلس على: {tweet_id}")
                
    except Exception as e: logger.error(f"Reply System Error: {e}")

# ================= 🧵 FUTURE MISSION (Smooth Threading) =================
async def run_mission():
    logger.info("📡 رصد تقنيات 2026 بأسلوب أنسني...")
    topics = [
        "أسرار معالجات Azure Maya 200", 
        "روبوتات Helix 02 في حياتنا اليومية", 
        "نظارات الواقع المعزز البديلة للجوال في 2026",
        "تطور الذكاء الاصطناعي في iOS 20"
    ]
    topic = random.choice(topics)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"latest unique features of {topic} 2026",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    sys_prompt = "أنت مهتم بالتقنية في 2026. اكتب ثريد 3 تغريدات بأسلوب سوالف تقنية ممتعة وسلسة. تحدث عن التقنية بحماس ومشاركة للخبر."
    content = await ask_ai(sys_prompt, f"المعرفة الخام:\n{knowledge}")
    if not content: return

    raw_tweets = [t for t in re.split(r'\n\n|\d+[./]\s', content) if len(t) > 30]
    
    prev_id = None
    for i, t in enumerate(raw_tweets[:3]):
        try:
            msg = f"{i+1}/3: {clean_pro(t)}"
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except Exception as e: logger.error(f"Tweet Error: {e}")

    logger.success(f"✅ تم نشر الثريد السلس: {topic}")

# ================= 🏁 MAIN LOOP =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V2600 Humanized Online | Mode: {mode}")
    if mode == "manual":
        # تنظيف اختياري للسجلات القديمة جداً
        limit_date = (datetime.now() - timedelta(days=7)).isoformat()
        db.execute("DELETE FROM logs WHERE date < ?", (limit_date,))
        db.commit()
        
        await run_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_mission, 'cron', hour='9,15,21') # نشر 3 مرات يومياً
    scheduler.add_job(smart_reply, 'interval', minutes=30) # فحص المنشنات كل نصف ساعة
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
