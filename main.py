import os
import asyncio
import httpx
import tweepy
import random
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

client = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🧠 محرك المحتوى المجدول (SCHEDULED ENGINE) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.8,
                    "messages": [
                        {"role": "system", "content": system + "\n- لهجة خليجية بيضاء.\n- ركز على التطبيق العملي والقيمة المضافة."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

async def generate_content_by_day():
    """يختار نمط المحتوى بناءً على يوم الأسبوع الحالي"""
    today_name = datetime.now().strftime('%A') # جلب اسم اليوم بالإنجليزية
    
    # 1. يوم الثلاثاء: يوم البرومبتات
    if today_name == "Tuesday":
        logger.info("🎯 اليوم هو الثلاثاء: تفعيل 'يوم البرومبت العالمي'")
        sys = "أنت خبير هندسة أوامر (Prompt Engineer). قدم برومبت إنجليزي احترافي لحل مشكلة فنية دقيقة مع شرح كيفية استخدامه."
        goal = "إنشاء برومبت إبداعي (Image/Video/Code) يقدم نتيجة مبهرة للمستخدم."
    
    # 2. يوم الجمعة: يوم المخططات (Blueprints)
    elif today_name == "Friday":
        logger.info("🏗️ اليوم هو الجمعة: تفعيل 'مخطط الأسبوع'")
        sys = "أنت مهندس أتمتة (Automation Architect). صمم سير عمل (Workflow) يربط بين أداتين أو أكثر للأفراد."
        goal = "شرح خطوات ربط تقني (n8n, APIs, Zapier) يحل مشكلة يومية ويوفر الوقت."
    
    # 3. بقية الأيام: تنويع (تحليلات، أخبار، نصائح دسمة)
    else:
        logger.info("🌀 يوم عادي: تفعيل نظام التنويع الاستراتيجي")
        random_type = random.choice(["تحليل تقني لخبر مسرب", "نصيحة تقنية عميقة للمحترفين", "مراجعة أداة AI جديدة"])
        sys = "أنت مستشار تقني أول (Senior Tech Consultant). ابحث عن العمق والقيمة المضافة."
        goal = f"تقديم {random_type} بأسلوب استقصائي يهم الأفراد."

    return await ask_ai(sys, f"اصنع محتوى فريداً لهذا اليوم هدفه: {goal}")

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("🛡️ تشغيل المحرك المجدول V22...")
    try:
        content = await generate_content_by_day()
        if content:
            # النشر (تغريدة طويلة للمشتركين)
            client.create_tweet(text=content)
            logger.success("✅ تم النشر بنجاح بناءً على جدول الأسبوع!")
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(main())
