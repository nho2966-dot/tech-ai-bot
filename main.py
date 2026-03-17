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

# ================= 🔐 الإعدادات (Secrets) =================
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

# إعداد عميل تويتر الموحد
twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# ذاكرة الحساب (لمنع التكرار)
DB_NAME = "tech_master_v1100.db"
db = sqlite3.connect(DB_NAME)
db.execute("CREATE TABLE IF NOT EXISTS logs (topic TEXT, date TEXT)")
db.commit()

# ================= 🛡️ فلتر "الهيبة التقنية" =================
def clean_pro(text):
    # حذف الرموز الصينية، الحشو الإنشائي، والكلمات الضعيفة
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    bad_words = ['يا جماعة', 'لا تقلقوا', 'مذهلة', 'يا شباب', 'اليوم جايب لكم', 'هل تعلمون', 'نصيحة اليوم']
    for word in bad_words:
        text = text.replace(word, '')
    # تنظيف المسافات الزائدة والترقيم العشوائي
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    return " ".join(text.split()).strip()

# ================= 🧠 محرك الذكاء (The Architect) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.2, # حرارة منخفضة لضمان الدقة ومنع الهلوسة
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            data = res.json()
            return data["choices"][0]["message"]["content"] if "choices" in data else None
    except Exception as e:
        logger.error(f"AI Engine Error: {e}")
        return None

# ================= 🔄 محرك البحث الذكي (Retry System) =================
async def get_knowledge(query, retries=3):
    for i in range(retries):
        try:
            logger.info(f"🔍 محاولة البحث {i+1} عن: {query}")
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post("https://api.tavily.com/search", json={
                    "api_key": CONF["TAVILY"], 
                    "query": query,
                    "search_depth": "advanced"
                })
                r.raise_for_status()
                return "\n".join([x['content'] for x in r.json().get("results", [])])
        except (httpx.ReadTimeout, httpx.ConnectError):
            logger.warning("⏳ تأخر الرد من محرك البحث، إعادة المحاولة...")
            await asyncio.sleep(10)
    return None

# ================= 🎥 صائد الفيديوهات القصيرة =================
async def find_video(topic):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], 
                "query": f"{topic} tutorial short video 2026 tiktok youtube",
                "max_results": 1
            })
            results = r.json().get("results", [])
            return results[0]['url'] if results else None
    except: return None

# ================= 📢 إشعارات تلغرام =================
async def send_tg_log(message):
    if not CONF['TG_TOKEN']: return
    try:
        url = f"https://api.telegram.org/bot{CONF['TG_TOKEN']}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": CONF['TG_CHAT_ID'], "text": f"🚀 تم النشر بنجاح:\n\n{message}"})
    except Exception as e: logger.error(f"TG Log Error: {e}")

# ================= 🧵 المهمة اليومية (Content Creation) =================
async def run_mission():
    logger.info("📡 جاري رصد أحدث التقنيات لعام 2026...")
    
    # قائمة التصنيفات الجديدة (الأسبوع القادم)
    categories = [
        "هندسة الأوامر (Prompt Engineering) لـ ChatGPT-5",
        "خفايا نظام macOS Sequoia والإنتاجية",
        "أدوات ذكاء اصطناعي لأتمتة المهام المكتبية",
        "تطور خوارزمية X (تويتر) وطرق زيادة الظهور 2026",
        "أسرار المنزل الذكي وربط الأجهزة المتعددة",
        "أمن العملات الرقمية وحماية المحافظ الباردة",
        "إعدادات كاميرا آيفون 17 برو الاحترافية"
    ]
    
    topic = random.choice(categories)
    
    # 1. البحث عن المعلومة
    knowledge = await get_knowledge(f"latest unique technical feature or hack for {topic} 2026")
    if not knowledge: return

    # 2. الصياغة ببرومبت الـ CTO الصارم
    sys_prompt = """أنت CTO تقني صارم. 
    المطلوب: استخلص 'خبيئة تقنية' واحدة حقيقية ودسمة لعام 2026.
    القواعد:
    - ابدأ بـ 'الزبدة التقنية' فوراً بدون مقدمات ترحيبية.
    - التغريدات تكون (1/3، 2/3، 3/3) فقط.
    - اللغة: خليجية بيضاء مهنية رصينة.
    - ممنوع: 'يا جماعة'، 'لا تقلقوا'، 'مذهلة'.
    - ممنوع أي لغة غير العربية (إلا المصطلحات التقنية)."""

    content = await ask_ai(sys_prompt, f"المعرفة الخام:\n{knowledge}")
    if not content: return

    # 3. جلب الفيديو
    video_url = await find_video(topic)

    # 4. النشر على X
    tweets = [clean_pro(t) for t in re.split(r'\d+[./]\s\d+|\n\n', content) if len(t) > 20]
    
    prev_id = None
    log_text = ""
    for i, t in enumerate(tweets[:3]):
        try:
            msg = f"{i+1}/3: {t}"
            if i == 2 and video_url:
                msg += f"\n\n📺 شرح مرئي:\n{video_url}"
            
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id, user_auth=True)
            prev_id = res.data["id"]
            log_text += f"{msg}\n---\n"
            await asyncio.sleep(15)
        except Exception as e: logger.error(f"Posting Error: {e}")

    # 5. التوثيق
    db.execute("INSERT INTO logs VALUES (?, ?)", (topic, datetime.now().isoformat()))
    db.commit()
    await send_tg_log(log_text)
    logger.success(f"✅ تم إنهاء المهمة بنجاح عن: {topic}")

# ================= 🏁 الحلقة الرئيسية =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V1300 Sovereign System Online | Mode: {mode}")
    if mode == "manual":
        await run_mission()
        return

    scheduler = AsyncIOScheduler()
    # النشر في أوقات الذروة (9 صباحاً، 4 عصراً، 10 مساءً)
    scheduler.add_job(run_mission, 'cron', hour='9,16,22')
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
