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

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
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

DB_NAME = "tech_master_v1100.db"
db = sqlite3.connect(DB_NAME)
db.execute("CREATE TABLE IF NOT EXISTS logs (topic TEXT, date TEXT)")
db.commit()

# ================= 🛡️ PRO CLEANER =================
def clean_pro(text):
    text = re.sub(r'(يا شباب|خبيئة مذهلة|اليوم جايب لكم|هل تعلمون|أهلاً بكم|عاجل|حصري|الزبدة)', '', text)
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    return " ".join(text.split()).strip()

# ================= 🧠 AI BRAIN =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- اللهجة: خليجية بيضاء مهنية."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            data = res.json()
            return data["choices"][0]["message"]["content"] if "choices" in data else None
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🔄 SMART SEARCH (With Retries) =================
async def get_knowledge(query, retries=3):
    for i in range(retries):
        try:
            logger.info(f"🔍 محاولة البحث رقم {i+1} عن: {query}...")
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post("https://api.tavily.com/search", json={
                    "api_key": CONF["TAVILY"], 
                    "query": query,
                    "search_depth": "advanced"
                })
                r.raise_for_status()
                results = r.json().get("results", [])
                if results:
                    return "\n".join([x['content'] for x in results])
        except (httpx.ReadTimeout, httpx.ConnectError):
            logger.warning(f"⏳ تأخر الرد، إعادة المحاولة بعد 10 ثواني...")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في البحث: {e}")
            break
    return None

# ================= 🎥 VIDEO SEARCH =================
async def find_video(topic):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], 
                "query": f"{topic} tutorial video youtube tiktok 2026",
                "max_results": 1
            })
            results = r.json().get("results", [])
            return results[0]['url'] if results else None
    except: return None

# ================= 🧵 MISSION =================
async def run_mission():
    logger.info("📡 بدء المهمة التقنية...")
    
    categories = [
        "تحديثات خوارزمية X وطرق التصدر 2026",
        "ميزات مخفية في iOS 19 للمحترفين",
        "أدوات AI Agent تنجز مهام البيزنس تلقائياً",
        "تريكات زيادة الوصول في تيك توك وإنستقرام",
        "أمن المعلومات وحماية البيانات الشخصية 2026"
    ]
    
    topic = random.choice(categories)
    
    # استخدام محرك البحث الجديد ذو المحاولات المتكررة
    knowledge = await get_knowledge(f"latest unique technical feature for {topic} March 2026")
    
    if not knowledge:
        logger.error("🚫 فشل البحث بعد عدة محاولات. يتم إيقاف الحلقة الحالية.")
        return

    sys_prompt = "أنت CTO تقني. استخرج ميزة واحدة حقيقية ودسمة. اكتب ثريد 3 تغريدات. ابدأ بالمشكلة وحلها فوراً."
    content = await ask_ai(sys_prompt, f"المعرفة المستخرجة:\n{knowledge}")
    if not content: return

    video_url = await find_video(topic)
    tweets = [clean_pro(t) for t in re.split(r'\n\n', content) if len(t) > 20]
    
    prev_id = None
    log_text = ""
    for i, t in enumerate(tweets[:3]):
        try:
            msg = f"{i+1}. {t}"
            if i == 2 and video_url: msg += f"\n\n📺 شرح مرئي:\n{video_url}"
            
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            log_text += f"{msg}\n"
            await asyncio.sleep(15)
        except Exception as e: logger.error(f"Post Error: {e}")

    db.execute("INSERT INTO logs VALUES (?, ?)", (topic, datetime.now().isoformat()))
    db.commit()
    logger.success(f"✅ تم النشر بنجاح: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V1200 Smart System Online | Mode: {mode}")
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
