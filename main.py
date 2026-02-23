import os
import asyncio
import random
import tweepy
from datetime import datetime, timedelta
from loguru import logger
from openai import OpenAI

# ==========================================
# ⚙️ الإعدادات والسيادة
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# ملف لحفظ الردود لمنع التكرار (قوانين X)
REPLY_LOG = "replied_ids.txt"

def has_replied(tweet_id):
    if not os.path.exists(REPLY_LOG): return False
    with open(REPLY_LOG, "r") as f: return str(tweet_id) in f.read()

def log_reply(tweet_id):
    with open(REPLY_LOG, "a") as f: f.write(f"{tweet_id}\n")

# ==========================================
# 🧠 صياغة الرد (وقار خليجي + تحليل)
# ==========================================
async def get_safe_reply(user_text):
    prompt = (
        f"رد بذكاء ووقار على هذا التعليق التقني: '{user_text}'. "
        "اللغة: خليجية بيضاء راقية. "
        "الشرط: لا تكرر الكلام، كن ملهماً ومختصراً جداً (أقل من 180 حرفاً)."
    )
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except: return None

# ==========================================
# 🛰️ رادار الردود المتوافق مع القوانين
# ==========================================
async def safe_reply_monitor(client_v2, bot_id):
    logger.info("🔍 فحص المنشن (بموجب قوانين X)...")
    try:
        mentions = client_v2.get_users_mentions(id=bot_id, max_results=5)
        if mentions.data:
            for tweet in mentions.data:
                if not has_replied(tweet.id):
                    reply = await get_safe_reply(tweet.text)
                    if reply:
                        client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                        log_reply(tweet.id)
                        logger.success(f"✅ تم الرد القانوني على: {tweet.id}")
                        await asyncio.sleep(random.randint(10, 30)) # فاصل زمني بين الردود
    except Exception as e:
        logger.warning(f"⚠️ تنبيه الـ API: {e}")

# ==========================================
# 🚀 انطلاق المنظومة (المجدول الآمن)
# ==========================================
async def main():
    logger.info("🔥 تشغيل أيبكس: نظام النشر والردود القانوني")
    client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
    
    try:
        bot_id = client_v2.get_me().data.id
    except:
        logger.error("❌ فشل الاتصال بـ X. تحقق من المفاتيح.")
        return

    while True:
        now_gulf = datetime.utcnow() + timedelta(hours=4)
        
        # 1. فحص الردود (كل 15 دقيقة لضمان عدم الحظر)
        await safe_reply_monitor(client_v2, bot_id)
        
        # 2. النشر في ساعة الذروة (1:00 PM)
        if now_gulf.hour == 13 and now_gulf.minute <= 5:
            # هنا يوضع كود النشر (المسابقة أو الحصاد)
            logger.info("🎯 ساعة أيبكس: جاري النشر...")
            # (يتم استدعاء دوال النشر السابقة هنا)
            await asyncio.sleep(600) # التوقف بعد النشر لضمان عدم التكرار

        # الانتظار العشوائي لنمط بشري
        wait_time = random.randint(600, 900) 
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(main())
