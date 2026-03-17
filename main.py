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

# ================= 🔐 إعدادات المفاتيح (من واقع الصورة) =================
CONF = {
    "XAI": os.getenv("XAI_API_KEY"), # استخدام Grok من xAI لمحتوى أكثر ذكاءً
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

# إعداد عميل تويتر
twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ الذاكرة والفلاتر =================
db = sqlite3.connect("tech_master_v1000.db")
db.execute("CREATE TABLE IF NOT EXISTS logs (topic TEXT, status TEXT, date TEXT)")
db.commit()

def clean_pro(text):
    # إزالة كل ما هو "آلي" أو "مكرر"
    text = re.sub(r'(يا شباب|خبيئة مذهلة|اليوم جايب لكم|هل تعلمون|أهلاً بكم|عاجل|حصري)', '', text)
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    return " ".join(text.split()).strip()

# ================= 🧠 محرك الذكاء (xAI Grok) =================
async def ask_grok(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['XAI']}"},
                json={
                    "model": "grok-beta", # أو الموديل المتوفر لديك
                    "messages": [
                        {"role": "system", "content": f"{system}\n- اللهجة: خليجية تقنية رصينة."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"xAI Error: {e}")
        return None

# ================= 📢 إشعار تلغرام =================
async def send_tg_log(message):
    try:
        url = f"https://api.telegram.org/bot{CONF['TG_TOKEN']}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": CONF['TG_CHAT_ID'], "text": f"🚀 تم نشر ثريد جديد:\n\n{message}"})
    except Exception as e:
        logger.error(f"Telegram Error: {e}")

# ================= 🎥 محرك الفيديو =================
async def find_visual_guide(topic):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], 
                "query": f"{topic} tutorial short video 2026 youtube tiktok",
                "include_domains": ["youtube.com", "tiktok.com"]
            })
            results = r.json().get("results", [])
            return results[0]['url'] if results else None
    except: return None

# ================= 🧵 المهمة الكبرى (The Master Mission) =================
async def run_master_mission():
    logger.info("📡 جاري إنتاج محتوى تقني نخبوي...")
    
    # تصنيفات المواكبة لعام 2026
    categories = [
        "خفايا نظام iOS 19 للمحترفين",
        "تحديثات خوارزمية X (تويتر) وكيفية التصدر",
        "أدوات الذكاء الاصطناعي التي تعمل كـ Agent شخصي",
        "ثغرات أمنية وطرق حماية الخصوصية في 2026",
        "أجهزة ومنتجات تقنية غريبة تم طرحها هذا الأسبوع"
    ]
    
    topic = random.choice(categories)
    
    # 1. البحث عن معلومة "طازجة"
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"new unique tech tip or breaking news about {topic} March 2026",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    # 2. صياغة الثريد عبر Grok
    sys_prompt = "أنت كبير مهندسين تقنيين. استخرج ميزة واحدة دسمة وحقيقية. اكتب ثريد 3-4 تغريدات. التغريدة الأولى تجذب الانتباه، الثانية خطوات، الثالثة الفائدة."
    content = await ask_grok(sys_prompt, f"المعرفة الحية:\n{knowledge}")
    if not content: return

    # 3. جلب فيديو توضيحي
    video_url = await find_visual_guide(topic)

    tweets = [clean_pro(t) for t in re.split(r'\n\n', content) if len(t) > 20]
    
    prev_id = None
    log_text = ""
    for i, t in enumerate(tweets[:4]):
        try:
            msg = f"{i+1}. {t}"
            if i == len(tweets[:4])-1 and video_url:
                msg += f"\n\n📺 شرح مرئي:\n{video_url}"
            
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            log_text += f"{msg}\n---\n"
            await asyncio.sleep(15)
        except Exception as e: logger.error(e)

    # 4. حفظ في الذاكرة وإرسال تلغرام
    db.execute("INSERT INTO logs VALUES (?, ?, ?)", (topic, "Published", datetime.now().isoformat()))
    db.commit()
    await send_tg_log(log_text)
    logger.success(f"✅ تم النشر بنجاح عن: {topic}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V1000 Master System Online | Mode: {mode}")
    if mode == "manual":
        await run_master_mission()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_master_mission, 'cron', hour='10,17,22') # نشر 3 مرات بمواقيت استراتيجية
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
