import os
import asyncio
import random
import tweepy
from datetime import datetime, timedelta
from loguru import logger
from openai import OpenAI

# ==========================================
# ⚙️ الإعدادات (OAuth 1.0a + V2)
# ==========================================
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

REPLY_LOG = "replied_ids.txt"

def has_replied(tweet_id):
    if not os.path.exists(REPLY_LOG): return False
    with open(REPLY_LOG, "r") as f: return str(tweet_id) in f.read()

def log_reply(tweet_id):
    with open(REPLY_LOG, "a") as f: f.write(f"{tweet_id}\n")

# ==========================================
# 🧠 محرك أيبكس (الوقار الخليجي)
# ==========================================
async def get_apex_content(prompt):
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت أيبكس، خبير تقني خليجي رصين. لغتك بيضاء راقية ومختصرة."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Brain Error: {e}")
        return None

# ==========================================
# ⚡ المهام التشغيلية
# ==========================================
async def run_apex_cycle(api_v1, client_v2, bot_id):
    now_gulf = datetime.utcnow() + timedelta(hours=4)
    
    # 1. رادار الردود (استخدام V1.1 كبديل مستقر للقراءة)
    try:
        # البحث عن المنشن باستخدام V1.1 (أكثر استقراراً في بعض باقات الاشتراك)
        mentions = await asyncio.to_thread(api_v1.mentions_timeline, count=5)
        for tweet in mentions:
            if not has_replied(tweet.id):
                logger.info(f"📩 معالجة تفاعل جديد من: @{tweet.user.screen_name}")
                reply_text = await get_apex_content(f"رد بوقار خليجي على: {tweet.text}")
                if reply_text:
                    client_v2.create_tweet(text=f"@{tweet.user.screen_name} {reply_text}", in_reply_to_tweet_id=tweet.id)
                    log_reply(tweet.id)
                    logger.success(f"✅ تم الرد على @{tweet.user.screen_name}")
                    await asyncio.sleep(5)
    except Exception as e:
        logger.warning(f"⚠️ تنبيه الرادار: {e}")

    # 2. النشر المجدول (ساعة أيبكس 1:00م)
    if now_gulf.hour == 13 and now_gulf.minute <= 10:
        logger.info("🎯 حانت ساعة النشر المجدول...")
        prompt = "صمم سؤال مسابقة تقنية ذكي. السطر1: السؤال، السطر2: 4 خيارات تفصلها فاصلة."
        content = await get_apex_content(prompt)
        if content and "\n" in content:
            lines = content.split("\n")
            opts = [o.strip() for o in lines[1].split(",")][:4]
            try:
                client_v2.create_tweet(text=f"🎁 مسابقة أيبكس:\n\n{lines[0]}", poll_options=opts, poll_duration_minutes=1440)
                logger.success("✅ تم نشر المسابقة بنجاح!")
            except Exception as e:
                logger.error(f"❌ فشل النشر: {e}")
        await asyncio.sleep(600)

async def main():
    logger.info("🔥 تشغيل أيبكس (نسخة الاشتراك المدفوع)...")
    try:
        # إعداد Auth مزدوج (V1 + V2) لضمان الصلاحيات
        auth = tweepy.OAuth1UserHandler(X_CRED["consumer_key"], X_CRED["consumer_secret"], 
                                      X_CRED["access_token"], X_CRED["access_token_secret"])
        api_v1 = tweepy.API(auth)
        client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
        
        bot_info = client_v2.get_me()
        bot_id = bot_info.data.id
        logger.success(f"✅ السيادة لـ @{bot_info.data.username} مفعلة.")

        while True:
            await run_apex_cycle(api_v1, client_v2, bot_id)
            await asyncio.sleep(300) # فحص كل 5 دقائق

    except Exception as e:
        logger.error(f"❌ خطأ تشغيل: {e}")

if __name__ == "__main__":
    asyncio.run(main())
