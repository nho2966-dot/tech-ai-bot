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
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ DYNAMIC MEMORY =================
db = sqlite3.connect("tech_secrets_v180.db")
db.execute("CREATE TABLE IF NOT EXISTS topics (topic TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY)")
db.commit()

def get_past_topics():
    cursor = db.execute("SELECT topic FROM topics")
    return [row[0] for row in cursor.fetchall()][-15:]

def save_topic(topic):
    db.execute("INSERT INTO topics (topic) VALUES (?)", (topic,))
    db.commit()

# ================= 🛡️ THE CLEANER =================
def clean_and_verify(text):
    forbidden = ["تعتبر هذه الميزة", "في هذا الثريد", "هل تعلم أن", "إليك الطريقة"]
    for word in forbidden: text = text.replace(word, "")
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#]', '', text)
    text = text.replace(". ", ".\n\n📍 ")
    return " ".join(text.split()).replace(".\n\n ", ".\n\n").strip()

# ================= 🧠 AI BRAIN =================
async def ask_ai(system, prompt, temp=0.7):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- اللهجة: خليجية بيضاء.\n- التخصص: أسرار التقنية للأفراد."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🧵 MISSION (Corrected Syntax) =================
async def run_daily_mission():
    # تم تصحيح علامات التنصيص هنا
    logger.info('🔍 جاري البحث عن "خبيئة تقنية" جديدة لعام 2026...')
    
    past_topics = get_past_topics()
    past_context = f"المواضيع السابقة: {', '.join(past_topics)}"

    topic_sys = f"""أنت خبير تقني داهية. ابحث عن ميزة مخفية أو اختصار ذكي في أدوات الـ AI أو الجوال لعام 2026.
    - التركيز: الفرد العادي.
    - ممنوع التكرار مع: {past_context}.
    - ابحث عن شيء صادم ومفيد جداً."""
    
    topic = await ask_ai(topic_sys, "أعطني عنواناً يشعل الفضول عن سر تقني.")
    
    if not topic: return
    save_topic(topic)

    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"hidden tricks and hacks for {topic} 2026",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    thread_sys = """اكتب ثريد (5 تغريدات) بأسلوب الخبايا والأسرار.
    - التغريدة الأولى: Hook قوي جداً.
    - البقية: شرح الخطوات بوضوح.
    - اللهجة: خليجية حماسية.
    - ممنوع الحشو."""
    
    raw_content = await ask_ai(thread_sys, f"السر: {topic}\nالتفاصيل: {knowledge}")
    
    tweets = [clean_and_verify(t) for t in re.split(r'\d+\s*[/-]\s*', raw_content) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:5]):
        try:
            full_text = f"{t}" if i == 0 else f"📍 {t}"
            res = twitter.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(10)
        except Exception as e: logger.error(e)

    logger.success(f"✅ تم كشف السر التقني عن: {topic}")

# ================= 🚀 EXECUTION =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V180 Fixed Online | Mode: {mode}")
    
    if mode == "manual":
        await run_daily_mission()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_mission, 'cron', hour=10)
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode))
