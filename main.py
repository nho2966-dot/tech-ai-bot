import os
import asyncio
import random
import tweepy
from datetime import datetime, timedelta
from loguru import logger
from openai import OpenAI
from google import genai

# ==========================================
# ⚙️ الربط والسيادة (Secrets)
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY")
}

X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

REPLY_LOG = "replied_ids.txt"

# --- وظائف صمام الأمان ---
def has_replied(tweet_id):
    if not os.path.exists(REPLY_LOG): return False
    with open(REPLY_LOG, "r") as f: return str(tweet_id) in f.read()

def log_reply(tweet_id):
    with open(REPLY_LOG, "a") as f: f.write(f"{tweet_id}\n")

# ==========================================
# 🧠 محرك الصياغة (اللغة الخليجية الراقية)
# ==========================================
async def get_apex_brain(prompt):
    # نستخدم Groq كعقل أساسي للسرعة والرزانة
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "أنت خبير تقني خليجي، لغتك رصينة، راقية، ومختصرة."},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except:
        return None

# ==========================================
# 🛰️ رادار الردود والمهام
# ==========================================
async def execute_tasks(client_v2, bot_id):
    now_gulf = datetime.utcnow() + timedelta(hours=4)
    
    # 1. فحص الردود (قانونياً)
    try:
        mentions = client_v2.get_users_mentions(id=bot_id, max_results=5)
        if mentions.data:
            for tweet in mentions.data:
                if not has_replied(tweet.id):
                    logger.info(f"📩 رد جديد على: {tweet.id}")
                    reply = await get_apex_brain(f"رد بوقار على: {tweet.text}")
                    if reply:
                        client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                        log_reply(tweet.id)
                        await asyncio.sleep(random.randint(10, 20)) # فاصل بشري
    except Exception as e: logger.error(f"Radar Error: {e}")

    # 2. النشر المجدول (ساعة أيبكس 1:00 ظهراً)
    if now_gulf.hour == 13 and now_gulf.minute <= 15:
        is_friday = now_gulf.weekday() == 4
        logger.info(f"🎯 ساعة أيبكس حانت (اليوم: {'جمعة' if is_friday else 'يوم عادي'})")
        
        if is_friday:
            prompt = "اكتب 'حصاد الأسبوع التقني' للأفراد بلهجة خليجية راقية. ركز على 3 أدوات AI زادت إنتاجيتك."
            content = await get_apex_brain(prompt)
            if content: client_v2.create_tweet(text=f"📌 حصاد الجمعة:\n\n{content}")
        else:
            prompt = "صمم سؤال مسابقة تقنية ذكي (اختيار من متعدد). السطر الأول السؤال، السطر الثاني 4 خيارات تفصلها فاصلة."
            raw = await get_apex_brain(prompt)
            if raw and "\n" in raw:
                lines = raw.split("\n")
                options = [o.strip() for o in lines[1].split(",")][:4]
                client_v2.create_tweet(text=f"🎁 مسابقة أيبكس:\n\n{lines[0]}", poll_options=options, poll_duration_minutes=1440)
        
        await asyncio.sleep(1000) # منع التكرار في نفس الساعة

# ==========================================
# 🚀 انطلاق المنظومة
# ==========================================
async def main():
    logger.info("🔥 نظام أيبكس قيد التشغيل الكامل...")
    try:
        client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
        bot_info = client_v2.get_me()
        bot_id = bot_info.data.id
        logger.success(f"✅ متصل كـ: @{bot_info.data.username}")

        while True:
            await execute_tasks(client_v2, bot_id)
            # فحص كل 10 دقائق (متوافق مع قوانين X)
            await asyncio.sleep(600)

    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")

if __name__ == "__main__":
    asyncio.run(main())
