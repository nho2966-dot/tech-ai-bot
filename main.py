import os
import asyncio
import httpx
import tweepy
from datetime import datetime, timedelta, timezone
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

# ================= 🛡️ فحص التكرار (LIVE AUDIT) =================
def get_recent_activity(bot_id):
    try:
        tweets = client.get_users_tweets(id=bot_id, max_results=50, tweet_fields=['text', 'created_at', 'attachments'], expansions='attachments.poll_ids')
        return tweets.data if tweets.data else []
    except: return []

def is_duplicate(text, recent_tweets):
    # بصمة النص (أول 40 حرف)
    fingerprint = text[:40].strip()
    for tw in recent_tweets:
        if fingerprint in tw.text: return True
    return False

# ================= 🧠 محرك التجديد (RENEWAL ENGINE) =================
async def generate_unique_content(recent_tweets):
    """يحاول توليد محتوى فريد عبر عدة محاولات إذا وجد تكراراً"""
    topics = [
        "أداة ذكاء اصطناعي جديدة للأفراد لم تُطرح في السوق بعد",
        "طريقة مبتكرة لاستخدام AI في تنظيم الوقت (Workflow)",
        "تحليل لميزة تقنية مسربة في هواتف 2026",
        "نصيحة تقنية غريبة وغير تقليدية لزيادة الإنتاجية"
    ]
    
    for attempt in range(5): # 5 محاولات لتوليد شيء جديد
        topic = random.choice(topics)
        logger.info(f"🔄 محاولة توليد محتوى فريد (رقم {attempt+1})...")
        
        sys_msg = "أنت محرر تقني خليجي استقصائي. ابحث عن فكرة نادرة وغير مكررة."
        prompt = f"اكتب تغريدة إبداعية عن: {topic}. تأكد أنها تختلف تماماً عن أي محتوى تقني تقليدي."
        
        content = await ask_ai(sys_msg, prompt)
        if content and not is_duplicate(content, recent_tweets):
            return content
            
    return None # إذا فشل بعد 5 محاولات (نادر الحدوث)

async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=40) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.9, # حرارة عالية لضمان التجدد وعدم التكرار
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
                }
            )
            return res.json()["choices"][0]["message"]["content"].strip()
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("🛡️ بدء نظام التجديد المستمر V16...")
    try:
        me = client.get_me().data
        bot_id = me.id
        recent_tweets = get_recent_activity(bot_id)

        # 1. فحص الاستطلاع الأسبوعي
        has_poll = False
        now = datetime.now(timezone.utc)
        for tw in recent_tweets:
            if tw.attachments and 'poll_ids' in tw.attachments:
                if (now - tw.created_at).days < 7:
                    has_poll = True
                    break

        # 2. توليد المحتوى
        if has_poll:
            logger.info("💡 الاستطلاع موجود، سأبحث عن 'سبق تقني' جديد...")
            unique_content = await generate_unique_content(recent_tweets)
            if unique_content:
                client.create_tweet(text=unique_content[:280])
                logger.success("🔥 تم نشر محتوى فريد وجديد تماماً!")
        else:
            # نشر استطلاع جديد (بشرط ألا يكون مكرر الأسئلة)
            logger.info("📊 جاري صياغة استطلاع أسبوعي جديد...")
            q = "في 2026، وش الأداة اللي غيرت مفهوم العمل عندك؟"
            opts = ["Agents الذكية", "نظارات AR", "أتمتة n8n", "أدوات التوليد الصوتي"]
            client.create_tweet(text=q, poll_options=opts, poll_duration_minutes=1440)
            logger.success("✅ تم نشر استطلاع الأسبوع.")

    except Exception as e:
        logger.error(f"❌ خطأ: {e}")

import random
if __name__ == "__main__":
    asyncio.run(main())
