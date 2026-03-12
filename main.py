import os
import re
import asyncio
import httpx
import tweepy
import sqlite3
import numpy as np
from loguru import logger
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG (V120) =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"], consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"], access_token_secret=CONF["X"]["access_s"]
)

# ================= 🛡️ ADVANCED CLEANER =================
def clean(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:()@#/-]', '', text)
    # إزالة حشو V90 الممل
    bad_starts = ["أهلاً بكم", "في هذا الثريد", "هل تعلم", "تخيل"]
    for s in bad_starts: text = text.replace(s, "")
    return " ".join(text.split()).strip()

# ================= 🧠 AI CALL (Multi-Purpose) =================
async def ask_ai(system, prompt, temp=0.5):
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONF['GROQ']}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": temp,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            }
        )
        return res.json()["choices"][0]["message"]["content"]

# ================= 🎨 IMAGE GEN (Visual Boost) =================
# ملاحظة: هنا نستخدم قدرة Gemini (Nano Banana 2) لتوليد وصف الصورة
async def generate_tech_image(topic):
    logger.info(f"🎨 جاري تصميم الهوية البصرية لموضوع: {topic}")
    prompt = f"A professional high-tech architecture diagram for {topic}, 3D isometric style, neon blue and dark grey theme, 8k resolution, cinematic lighting."
    # في البيئة الحقيقية، ستقوم باستدعاء image_generation(prompt) هنا.
    return "image_url_placeholder" 

# ================= 🧵 THREAD & LINKEDIN GENERATOR =================
async def generate_multimodal_content(topic, knowledge):
    # 1. ثريد تويتر (خليجي تقني حار)
    x_sys = "أنت CTO تقني حريف. اكتب ثريد من 5 تغريدات. ابدأ بالـ Architecture فوراً. اذكر أدوات محددة (CrewAI, Supabase, LangGraph)."
    x_thread = await ask_ai(x_sys, f"الموضوع: {topic}\nالمعرفة: {knowledge}", 0.6)
    
    # 2. منشور لينكد إن (بروفيشينال رصين)
    li_sys = "أنت Senior Solution Architect. اكتب منشور LinkedIn احترافي يشرح الجدوى الاقتصادية والتقنية لهذا الحل للأفراد والشركات."
    li_post = await ask_ai(li_sys, f"الموضوع: {topic}\nالمعرفة: {knowledge}", 0.4)
    
    return x_thread, li_post

# ================= 🚀 EXECUTION ENGINE =================
async def daily_empire_mission():
    logger.info("🦁 تبدأ مهمة الإمبراطورية اليومية...")
    
    # 1. اكتشاف (Trend Discovery)
    topic = await ask_ai("محلل ترند", "أعطني موضوع AI Agent أو RAG عميق للأفراد.", 0.7)
    if not topic: return

    # 2. بحث (Advanced Research)
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": topic, "search_depth": "advanced"})
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    # 3. توليد المحتوى (Twitter + LinkedIn)
    x_thread, li_post = await generate_multimodal_content(topic, knowledge)
    
    # 4. توليد الصورة (Visuals)
    image_url = await generate_tech_image(topic)

    # 5. النشر على X (ثريد مرتب)
    tweets = [clean(t) for t in re.split(r'\d+\s*[/-]\s*', x_thread) if len(t) > 30]
    prev_id = None
    for i, t in enumerate(tweets[:5]):
        text = f"{i+1}/ {t}"
        if prev_id is None:
            # هنا نرفق الصورة في أول تغريدة
            res = twitter.create_tweet(text=text) # أضف media_ids هنا لو رفعت الصورة
        else:
            res = twitter.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
        prev_id = res.data["id"]
        await asyncio.sleep(5)
    
    logger.success(f"🔥 تم اجتياح المنصات بموضوع: {topic}")

# ================= 📅 SCHEDULER =================
scheduler = AsyncIOScheduler()
scheduler.add_job(daily_empire_mission, "cron", hour=10) # 10 صباحاً وقت الذروة
scheduler.start()

async def main():
    logger.info("🚀 V120 AI Media Engine: ONLINE")
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
