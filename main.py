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

twitter = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ MEMORY (منع التكرار والحفاظ على الحداثة) =================
db = sqlite3.connect("tech_master_v350.db")
db.execute("CREATE TABLE IF NOT EXISTS topics (topic TEXT)")
db.commit()

def save_topic(topic):
    db.execute("INSERT INTO topics (topic) VALUES (?)", (topic,))
    db.commit()

def get_past_topics():
    return [row[0] for row in db.execute("SELECT topic FROM topics").fetchall()][-20:]

# ================= 🛡️ CLEANER (الفلتر الخليجي الحاد) =================
def clean_text(text):
    # منع الرموز الغريبة والهلوسة اللغوية
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    # إزالة الأرقام التلقائية وحشو الجمل
    text = re.sub(r'^\d+[:/-]\s*', '', text)
    forbidden = ["يا شباب", "أهلاً بكم", "جربوا هالحركة", "في هذا الثريد"]
    for word in forbidden: text = text.replace(word, "")
    # تنسيق النقاط
    text = text.replace(". ", ".\n\n📍 ")
    return " ".join(text.split()).replace(".\n\n ", ".\n\n").strip()

# ================= 🧠 AI BRAIN (The Tech Consultant) =================
async def ask_ai(system, prompt, temp=0.1): # حرارة منخفضة جداً للالتزام بالواقع
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": f"{system}\n- الشخصية: مستشار تقني خليجي رصين.\n- القواعد: لا تأليف، لا خيال، لا إشعاعات وهمية."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🧵 MISSION (Uncovering Real Value) =================
async def run_daily_mission():
    logger.info("📡 جاري البحث عن خبيئة تقنية 'حقيقية'...")
    
    # 1. تحديد نطاق البحث (تغيير النطاق يومياً لضمان التنوع)
    scopes = [
        "أسرار مخفية في إنستقرام و تيك توك لزيادة الوصول للأفراد 2026",
        "حيل إنتاجية في أدوات AI مثل Claude و ChatGPT و Notion للأفراد",
        "خبايا في نظام iOS و Android تسرع العمل وتوفر الجهد",
        "أدوات إنترنت خفية (Web Tools) تسهل حياة المستخدم اليومية"
    ]
    current_scope = scopes[len(get_past_topics()) % len(scopes)]
    
    # 2. البحث في Tavily عن الحقائق
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": CONF["TAVILY"], 
            "query": f"real hidden tips and professional hacks for {current_scope}",
            "search_depth": "advanced",
            "max_results": 5
        })
        knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

    # 3. استخلاص وصياغة المحتوى
    system_prompt = """أنت CTO مخضرم. استخرج من المعلومات المرفقة 'خبيئة' واحدة دسمة وحقيقية.
    المطلوب ثريد (4 تغريدات):
    1. اذكر المشكلة والحل (الخبيئة) فوراً.
    2. خطوات التطبيق 1، 2، 3.
    3. ميزة إضافية أو تحذير تقني.
    - اللهجة: خليجية بيضاء، احترافية، بدون حشو."""
    
    raw_content = await ask_ai(system_prompt, f"المعلومات الموثقة:\n{knowledge}")
    
    if not raw_content: return
    
    tweets = [clean_text(t) for t in re.split(r'\n\n', raw_content) if len(t) > 20]
    
    prev_id = None
    for i, t in enumerate(tweets[:4]):
        try:
            full_text = f"{i+1}/ {t}"
            res = twitter.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(12)
        except Exception as e: logger.error(e)

    save_topic(current_scope)
    logger.success("✅ تم النشر بنجاح.")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V350 Tech Master Online | Mode: {mode}")
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
