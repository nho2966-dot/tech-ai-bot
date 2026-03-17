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

# ================= 🔐 الإعدادات =================
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

# عميل تويتر الموحد بصلاحيات المستخدم الكاملة (لحل خطأ 401)
twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# ================= 🗄️ الذاكرة (Memory) =================
db = sqlite3.connect("tech_master_v600.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, type TEXT, timestamp DATETIME)")
db.commit()

# ================= 🛡️ الفلتر الصارم (قتل الابتذال) =================
def pro_cleaner(text):
    # إزالة لغة "المسوقين" المستهلكة
    text = re.sub(r'(يا شباب|خبيئة مذهلة|اليوم جايب لكم|هل تعلمون|نصيحة اليوم|Stay tuned|يا ناس|ميزة دسمة|أهلاً بكم)', '', text)
    # تنظيف الترقيم المصطنع
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    text = re.sub(r'\d+[\s.]+\d+[:/]\s*', '', text)
    # حذف الرموز غير الضرورية
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    return " ".join(text.split()).strip()

# ================= 🧠 محرك الذكاء (Zero-Banter Engine) =================
async def ask_ai(system, prompt, temp=0.1): # حرارة منخفضة جداً للالتزام بالحقائق
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- ممنوع ذكر: تنظيف الذاكرة، توفير البطارية، تسريع الإنترنت التقليدي.\n- اللهجة: خليجية تقنية حادة."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🧵 المهمة اليومية (نشر الخبايا الحقيقية) =================
async def run_daily_mission():
    logger.info("📡 جاري التنقيب عن خبايا تقنية نادرة لعام 2026...")
    
    # مسارات المحتوى النخبوي
    scenarios = [
        "خبايا خوارزمية تيك توك وإنستقرام لزيادة الانتشار العضوي 2026 للأفراد",
        "تريكات احترافية في استخدام وكلاء الذكاء الاصطناعي ChatGPT-5 لتنفيذ مهام معقدة",
        "ميزات مخفية في نظام iOS 19 أو Android 16 تهم المحترفين والأفراد",
        "أدوات أتمتة (Automation) تربط تطبيقات التواصل الاجتماعي بالذكاء الاصطناعي",
        "خبايا تقنية في المتصفحات الحديثة تمنع تتبع الشركات للإعلانات نهائياً"
    ]
    
    query = random.choice(scenarios)

    # البحث عن معلومات حية
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"precise technical steps and unique hacks for {query}",
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    sys_prompt = """أنت CTO متمرد وخبير تقني. استخلص ميزة واحدة 'حقيقية ودسمة' من البحث.
    المطلوب ثريد 3 تغريدات:
    1. 'الزبدة التقنية' فوراً بدون مقدمات أو كلمات ترحيب.
    2. خطوات التفعيل (1، 2، 3) بأسماء قوائم دقيقة.
    3. نصيحة للمحترفين أو تحذير تقني.
    - الأسلوب: تقني حاد، مباشر، خليجي بيضاء.
    - ممنوع: الهاشتاقات الكثيرة، كلمة 'خبيئة'."""
    
    content = await ask_ai(sys_prompt, f"المعرفة الحية:\n{knowledge}")
    if not content: return

    tweets = [pro_cleaner(t) for t in re.split(r'\n\n', content) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:3]):
        try:
            final_text = f"{i+1}/ {t}"
            # استخدام user_auth=True لضمان الصلاحيات
            res = twitter.create_tweet(text=final_text, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except Exception as e: logger.error(f"X Post Error: {e}")
    logger.success(f"✅ تم نشر الثريد النخبوي عن: {query}")

# ================= 💬 الردود الذكية (Smart & Human) =================
async def smart_reply():
    try:
        # جلب المعرف الشخصي
        me = twitter.get_me(user_auth=True).data.id
        mentions = twitter.get_users_mentions(id=me, user_auth=True, max_results=5)
        
        if not mentions or not mentions.data: return

        for tweet in mentions.data:
            if db.execute("SELECT id FROM memory WHERE id=?", (tweet.id,)).fetchone(): continue
            
            logger.info(f"📩 منشن جديد من: {tweet.text[:30]}")
            reply_sys = "أنت مهندس تقني خليجي. رد على المنشن باختصار وذكاء. إذا سأل عن معلومة، أعطه الزبدة التقنية."
            answer = await ask_ai(reply_sys, tweet.text, temp=0.5)
            
            if answer:
                twitter.create_tweet(text=pro_cleaner(answer), in_reply_to_tweet_id=tweet.id, user_auth=True)
                db.execute("INSERT INTO memory (id, type, timestamp) VALUES (?, ?, ?)", (tweet.id, "reply", datetime.now()))
                db.commit()
                logger.info(f"✅ تم الرد على {tweet.id}")
                await asyncio.sleep(10)
    except Exception as e:
        logger.error(f"Reply Error (401 Check): {e}")

# ================= 🏁 الحلقة الرئيسية =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V600 Sovereign Online | Mode: {mode}")
    
    if mode == "manual":
        await run_daily_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    # النشر مرتين يومياً (10 صباحاً و 9 مساءً)
    scheduler.add_job(run_daily_mission, 'cron', hour='10,21')
    # الردود كل 15 دقيقة
    scheduler.add_job(smart_reply, 'interval', minutes=15)
    
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
