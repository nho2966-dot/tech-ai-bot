import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
from loguru import logger
from dotenv import load_dotenv
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

# الحل الجذري لخطأ AttributeError: استخدام Client الموحد
# يدعم العمليات المتزامنة وغير المتزامنة حسب الحاجة
twitter = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# ================= 🗄️ MEMORY (Updated Name) =================
# تأكد أن هذا الاسم هو نفسه الموجود في ملف الـ YAML
DB_NAME = "tech_secrets_v250.db"
db = sqlite3.connect(DB_NAME)
db.execute("CREATE TABLE IF NOT EXISTS topics (topic TEXT)")
db.commit()

def get_past_topics():
    cursor = db.execute("SELECT topic FROM topics")
    return [row[0] for row in cursor.fetchall()][-20:]

def save_topic(topic):
    db.execute("INSERT INTO topics (topic) VALUES (?)", (topic,))
    db.commit()

# ================= 🛡️ CLEANER =================
def clean_text(text):
    # مسح الرموز واللغات الغريبة (الصينية وغيرها)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    # مسح أرقام التعداد في بداية الجمل
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    # تنسيق مريح للعين
    text = text.replace(". ", ".\n\n📍 ")
    return " ".join(text.split()).replace(".\n\n ", ".\n\n").strip()

# ================= 🧠 AI BRAIN =================
async def ask_ai(system, prompt, temp=0.3):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- اللهجة: خليجية بيضاء.\n- التخصص: خبايا تقنية للأفراد."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🧵 MISSION =================
async def run_daily_mission():
    logger.info("🔍 جاري استخراج أسرار تقنية جديدة...")
    
    past = get_past_topics()
    context = f"ممنوع تكرار: {', '.join(past)}"

    topic_sys = f"أنت خبير خبايا تقنية للأفراد. ابحث عن ميزة مخفية في آيفون أو أندرويد أو تطبيقات AI لعام 2026 تهم المتابع العادي.\n{context}"
    topic = await ask_ai(topic_sys, "أعطني عنواناً لسر تقني.")
    
    if not topic: return
    save_topic(topic)

    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"hidden tricks for {topic} 2026 for personal use",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    thread_sys = "اكتب ثريد (4 تغريدات) بلهجة خليجية ذكية للأفراد. ابدأ بالزبدة ثم الخطوات. ممنوع الحشو."
    raw_content = await ask_ai(thread_sys, f"الموضوع: {topic}\nالمعلومات: {knowledge}")
    
    tweets = [clean_text(t) for t in re.split(r'\n\n', raw_content) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:4]):
        try:
            full_text = f"{i+1}/ {t}"
            res = twitter.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"X Post Error: {e}")

    logger.success(f"🔥 تم نشر الخبيئة بنجاح: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V250 Fixed Online | Mode: {mode}")
    if mode == "manual":
        await run_daily_mission()
        return
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_mission, 'cron', hour=10)
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=mode))
