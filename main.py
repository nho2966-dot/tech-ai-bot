import os
import asyncio
import random
import tweepy
from datetime import datetime, timedelta
from loguru import logger
from openai import OpenAI

# ==========================================
# ⚙️ إعدادات المفاتيح (تأكد من Github Secrets)
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

REPLY_LOG = "replied_ids.txt"

# --- وظائف صمام الأمان لمنع تكرار الردود ---
def has_replied(tweet_id):
    if not os.path.exists(REPLY_LOG): return False
    with open(REPLY_LOG, "r") as f: return str(tweet_id) in f.read()

def log_reply(tweet_id):
    with open(REPLY_LOG, "a") as f: f.write(f"{tweet_id}\n")

# ==========================================
# 🧠 محرك صياغة المحتوى (الوقار الخليجي)
# ==========================================
async def get_apex_content(prompt):
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
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
        logger.error(f"خطأ في محرك الذكاء: {e}")
        return None

# ==========================================
# 🛰️ منظومة النشر والرد الذكي
# ==========================================
async def run_apex_cycle(client_v2, bot_id):
    now_gulf = datetime.utcnow() + timedelta(hours=4)
    
    # 1. رادار الردود الذكية (بما أن حسابك مدفوع)
    try:
        mentions = client_v2.get_users_mentions(id=bot_id, max_results=5)
        if mentions and mentions.data:
            for tweet in mentions.data:
                if not has_replied(tweet.id):
                    logger.info(f"📩 اكتشاف منشن جديد: {tweet.id}")
                    reply_prompt = f"رد بوقار وذكاء على تعليق المتابع: {tweet.text}"
                    reply_text = await get_apex_content(reply_prompt)
                    
                    if reply_text:
                        client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                        log_reply(tweet.id)
                        logger.success(f"✅ تم الرد بذكاء على: {tweet.id}")
                        await asyncio.sleep(random.randint(5, 10)) # فاصل طبيعي
    except Exception as e:
        logger.warning(f"⚠️ تنبيه في الرادار (قد يكون بسبب الصلاحيات): {e}")

    # 2. النشر المجدول (ساعة أيبكس 1:00 ظهراً)
    if now_gulf.hour == 13 and now_gulf.minute <= 10:
        logger.info("🎯 حانت ساعة أيبكس للنشر المجدول...")
        
        # اختيار نوع المحتوى (حصاد الجمعة أو مسابقة)
        is_friday = now_gulf.weekday() == 4
        if is_friday:
            prompt = "اكتب حصاداً تقنياً مختصراً للأسبوع يركز على أدوات AI للأفراد بأسلوب خليجي ممتع."
            content = await get_apex_content(prompt)
            if content: client_v2.create_tweet(text=f"📌 حصاد الجمعة من أيبكس:\n\n{content}")
        else:
            prompt = "صمم سؤال مسابقة تقنية ذكي (اختيار من متعدد). السطر1: السؤال، السطر2: 4 خيارات تفصلها فاصلة."
            content = await get_apex_content(prompt)
            if content and "\n" in content:
                lines = content.split("\n")
                opts = [o.strip() for o in lines[1].split(",")][:4]
                client_v2.create_tweet(text=f"🎁 مسابقة أيبكس:\n\n{lines[0]}", poll_options=opts, poll_duration_minutes=1440)
        
        logger.success("✅ تم النشر المجدول بنجاح!")
        await asyncio.sleep(600) # منع التكرار في نفس الساعة

# ==========================================
# 🚀 التشغيل الرئيسي
# ==========================================
async def main():
    logger.info("🔥 انطلاق أيبكس: إصدار النجاح والاستقرار...")
    try:
        # الربط والتحقق من الصلاحيات
        client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
        bot_info = client_v2.get_me()
        bot_id = bot_info.data.id
        logger.success(f"✅ متصل بنجاح كـ: @{bot_info.data.username}")

        while True:
            await run_apex_cycle(client_v2, bot_id)
            # فحص كل 5 دقائق لضمان التفاعل الحي
            await asyncio.sleep(300)

    except Exception as e:
        logger.error(f"❌ فشل فادح في التشغيل: {e}")

if __name__ == "__main__":
    asyncio.run(main())
