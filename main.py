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

twitter = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ MEMORY =================
db = sqlite3.connect("tech_master_v500.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, type TEXT, timestamp DATETIME)")
db.commit()

# ================= 🛡️ PRO FILTER (قتل الابتذال) =================
def pro_cleaner(text):
    # إزالة لغة "اليوتيوبرز" المستهلكة
    text = re.sub(r'(يا شباب|خبيئة مذهلة|اليوم جايب لكم|هل تعلمون|نصيحة اليوم|Stay tuned|يا ناس)', '', text)
    # تنظيف الترقيم لتبدو كأنها كتابة خبير حقيقي
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    return " ".join(text.split()).strip()

# ================= 🧠 AI BRAIN (The Rationalist) =================
async def ask_ai(system, prompt, temp=0.1): # حرارة منخفضة جداً لضمان الواقعية
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- القواعد: لا تأليف، لا نصائح بدائية، لا إشاعات."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🧵 AUTO POST (الخبايا العميقة) =================
async def run_daily_mission():
    logger.info("📡 البحث عن ميزة تقنية 'حقيقية' وحصرية لعام 2026...")
    
    # البحث عن أخبار تقنية عميقة (Deep Tech Search)
    search_queries = [
        "new hidden features in iOS 19.4 March 2026",
        "advanced productivity hacks for ChatGPT-5 agents 2026",
        "secret features in Instagram professional mode 2026",
        "hidden browser dev tools for non-developers 2026"
    ]
    query = search_queries[datetime.now().day % len(search_queries)]
    
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": query,
            "search_depth": "advanced"
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    sys_prompt = """أنت Senior Tech Consultant. استخرج ميزة واحدة دسمة من النص المرفق.
    اكتب ثريد (3 تغريدات) بأسلوب خليجي تقني راقٍ:
    1. الميزة والقيمة (بدون مقدمات).
    2. الخطوات العملية.
    3. نصيحة للمحترفين.
    - ممنوع استخدام كلمة 'خبيئة' أو 'سر'. استخدم 'ميزة'، 'تعديل'، 'تريك'."""
    
    content = await ask_ai(sys_prompt, f"المعلومات من الويب:\n{knowledge}")
    if not content: return

    tweets = [pro_cleaner(t) for t in re.split(r'\n\n', content) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:3]):
        try:
            msg = f"{i+1}/ {t}"
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(15)
        except Exception as e: logger.error(e)
    logger.success("✅ تم نشر المحتوى الموثق.")

# ================= 💬 SMART REPLY (أنسنة مهذبة) =================
async def smart_reply():
    try:
        me = twitter.get_me().data.id
        mentions = twitter.get_users_mentions(id=me, max_results=5)
        if not mentions.data: return

        for tweet in mentions.data:
            if db.execute("SELECT id FROM memory WHERE id=?", (tweet.id,)).fetchone(): continue
            
            reply_sys = "أنت خبير تقني خليجي. رد على المنشن بذكاء واختصار. إذا كان السؤال تافهاً، أعطه معلومة تقنية دسمة بدلاً منه."
            answer = await ask_ai(reply_sys, tweet.text, temp=0.5)
            
            if answer:
                twitter.create_tweet(text=pro_cleaner(answer), in_reply_to_tweet_id=tweet.id)
                db.execute("INSERT INTO memory (id, type, timestamp) VALUES (?, ?, ?)", (tweet.id, "reply", datetime.now()))
                db.commit()
    except Exception as e: logger.error(e)

# ================= 🏁 AUTOMATION =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V500 Investigator Online | Mode: {mode}")
    if mode == "manual":
        await run_daily_mission()
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_mission, 'cron', hour='10,21') # نشر 10 صباحاً و 9 مساءً
    scheduler.add_job(smart_reply, 'interval', minutes=15)
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    arg_mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=arg_mode))
