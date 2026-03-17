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
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG (استخدام المفاتيح الموثوقة) =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"), # نعود لـ Groq لضمان الاستقرار
    "TAVILY": os.getenv("TAVILY_KEY"),
    "TG_TOKEN": os.getenv("TG_TOKEN"),
    "TG_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
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

# تصحيح اسم قاعدة البيانات ليتوافق مع الـ Artifacts
DB_NAME = "tech_master_v1100.db"
db = sqlite3.connect(DB_NAME)
db.execute("CREATE TABLE IF NOT EXISTS logs (topic TEXT, date TEXT)")
db.commit()

# ================= 🛡️ PRO CLEANER =================
def clean_pro(text):
    # تنظيف صارم لضمان هيبة الـ CTO
    text = re.sub(r'(يا شباب|خبيئة مذهلة|اليوم جايب لكم|هل تعلمون|أهلاً بكم|عاجل|حصري|الزبدة)', '', text)
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    return " ".join(text.split()).strip()

# ================= 🧠 AI BRAIN (The Stable Engine) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- اللهجة: خليجية بيضاء مهنية.\n- الهدف: فائدة حقيقية 2026."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            data = res.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"AI Response Error: {data}")
                return None
    except Exception as e:
        logger.error(f"Request Error: {e}")
        return None

# ================= 📢 TELEGRAM LOG =================
async def send_tg_log(message):
    if not CONF['TG_TOKEN']: return
    try:
        url = f"https://api.telegram.org/bot{CONF['TG_TOKEN']}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": CONF['TG_CHAT_ID'], "text": f"🚀 تم النشر:\n\n{message}"})
    except Exception as e: logger.error(f"TG Error: {e}")

# ================= 🎥 VIDEO SEARCH =================
async def find_video(topic):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], 
                "query": f"{topic} tutorial video youtube tiktok 2026",
                "max_results": 1
            })
            results = r.json().get("results", [])
            return results[0]['url'] if results else None
    except: return None

# ================= 🧵 MISSION (Diverse & High Value) =================
async def run_mission():
    logger.info("📡 جاري إنتاج محتوى تقني مواكب...")
    
    categories = [
        "تحديثات خوارزمية X (تويتر) وطرق التصدر 2026",
        "ميزات مخفية في iOS 19 للمحترفين",
        "أدوات AI Agent تنجز مهام البيزنس تلقائياً",
        "تريكات زيادة الوصول في تيك توك وإنستقرام",
        "أمن المعلومات وحماية البيانات الشخصية 2026"
    ]
    
    topic = random.choice(categories)
    
    # 1. البحث عن معلومة "طازجة" من Tavily
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"latest unique technical feature for {topic} March 2026",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    # 2. الصياغة بأسلوب مهندس
    sys_prompt = "أنت CTO تقني. استخرج ميزة واحدة حقيقية ودسمة. اكتب ثريد 3 تغريدات. ابدأ بالمشكلة وحلها فوراً."
    content = await ask_ai(sys_prompt, f"المعرفة:\n{knowledge}")
    if not content: return

    video_url = await find_video(topic)
    tweets = [clean_pro(t) for t in re.split(r'\n\n', content) if len(t) > 20]
    
    prev_id = None
    log_text = ""
    for i, t in enumerate(tweets[:3]):
        try:
            msg = f"{i+1}. {t}"
            if i == 2 and video_url:
                msg += f"\n\n📺 شرح مرئي:\n{video_url}"
            
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            log_text += f"{msg}\n"
            await asyncio.sleep(15)
        except Exception as e: logger.error(e)

    db.execute("INSERT INTO logs VALUES (?, ?)", (topic, datetime.now().isoformat()))
    db.commit()
    await send_tg_log(log_text)
    logger.success(f"✅ تم نشر الثريد عن: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V1100 Stable Online | Mode: {mode}")
    if mode == "manual":
        await run_mission()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_mission, 'cron', hour='10,18,22')
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
