import os
import asyncio
import random
import tweepy
from datetime import datetime, timedelta
from loguru import logger
from openai import OpenAI

# ==========================================
# ⚙️ الإعدادات (تركيز كامل على النشر V2)
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# ==========================================
# 🧠 محرك صناعة المحتوى (الذكاء الاصطناعي للأفراد)
# ==========================================
async def get_apex_content(prompt_type="news"):
    system_msg = "أنت أيبكس، خبير تقني خليجي رصين. تركز على تطبيقات الذكاء الاصطناعي التي تفيد الأفراد في حياتهم اليومية."
    
    prompts = {
        "news": "اكتب تغريدة عن أداة ذكاء اصطناعي جديدة ومذهلة تفيد الأفراد (مثل تنظيم الوقت أو التصميم). الأسلوب خليجي رصين مع هاشتاقات ذكية.",
        "poll": "صمم سؤال مسابقة ذكي عن AI. السطر1: السؤال، السطر2: 4 خيارات تفصلها فاصلة.",
        "tip": "أعط نصيحة تقنية سريعة لمستخدمي الهواتف لزيادة الإنتاجية باستخدام أدوات الذكاء الاصطناعي."
    }

    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompts[prompt_type]}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"خطأ في المحرك: {e}")
        return None

# ==========================================
# 🛰️ منظومة البث الاستراتيجي
# ==========================================
async def run_apex_broadcast(client_v2):
    now_gulf = datetime.utcnow() + timedelta(hours=4)
    
    # 1. النشر الصباحي (نصيحة تقنية) - الساعة 9 صباحاً
    if now_gulf.hour == 9 and now_gulf.minute <= 5:
        content = await get_apex_content("tip")
        if content:
            client_v2.create_tweet(text=f"💡 إشراقة تقنية:\n\n{content}")
            logger.success("✅ تم نشر النصيحة الصباحية.")
            await asyncio.sleep(600)

    # 2. ساعة الذروة (المسابقة) - الساعة 1 ظهراً
    if now_gulf.hour == 13 and now_gulf.minute <= 5:
        content = await get_apex_content("poll")
        if content and "\n" in content:
            lines = content.split("\n")
            opts = [o.strip() for o in lines[1].split(",")][:4]
            client_v2.create_tweet(text=f"🎁 مسابقة أيبكس اليومية:\n\n{lines[0]}", poll_options=opts, poll_duration_minutes=1440)
            logger.success("✅ تم نشر المسابقة.")
            await asyncio.sleep(600)

    # 3. النشر المسائي (أداة جديدة) - الساعة 8 مساءً
    if now_gulf.hour == 20 and now_gulf.minute <= 5:
        content = await get_apex_content("news")
        if content:
            client_v2.create_tweet(text=f"🚀 أداة اليوم من أيبكس:\n\n{content}")
            logger.success("✅ تم نشر أداة اليوم.")
            await asyncio.sleep(600)

async def main():
    logger.info("🔥 تشغيل أيبكس (إصدار البث الاستراتيجي)...")
    try:
        client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
        bot_info = client_v2.get_me()
        logger.success(f"✅ متصل كـ: @{bot_info.data.username}")

        while True:
            await run_apex_broadcast(client_v2)
            # فحص كل 4 دقائق للتأكد من مواعيد النشر
            await asyncio.sleep(240)

    except Exception as e:
        logger.error(f"❌ خطأ في التشغيل: {e}")

if __name__ == "__main__":
    asyncio.run(main())
