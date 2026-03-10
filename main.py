import os
import asyncio
import httpx
import tweepy
import random
import sqlite3
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

# ================= 🗂 DATABASE =================
def init_db():
    with sqlite3.connect("newsroom_v5.db") as db:
        db.execute("CREATE TABLE IF NOT EXISTS seen_mentions (id TEXT PRIMARY KEY)")
        db.execute("CREATE TABLE IF NOT EXISTS daily_post (date TEXT PRIMARY KEY)")
        db.commit()

# ================= 🧠 AI ENGINE =================
async def ask_ai(system, prompt, temperature=0.7):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system + """
- اللهجة: خليجية بيضاء رصينة وعملية.
- الإشارات: أشر للحسابات الرسمية ذات الصلة (مثل @OpenAI, @n8n_io, @Google, @AnthropicAI).
- الهاشتاقات: أضف 3-4 هاشتاقات تقنية ذكية في نهاية التغريدة (مثل #الذكاء_الاصطناعي #تقنية #أتمتة #هندسة_الأوامر).
- الجودة: القيمة المضافة فوق كل شيء."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 💬 MENTIONS (الردود الذكية) =================
async def handle_mentions():
    logger.info("🔍 فحص المنشنات مع الوسوم والإشارات...")
    try:
        me = client.get_me().data
        bot_id = str(me.id)
        mentions = client.get_users_mentions(id=bot_id, tweet_fields=['author_id', 'id', 'text', 'created_at'], max_results=15).data
        if not mentions: return

        threshold_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        processed_users = set()

        with sqlite3.connect("newsroom_v5.db") as db:
            for t in mentions:
                tweet_id, author_id = str(t.id), str(t.author_id)
                if t.created_at < threshold_24h or author_id == bot_id: continue
                if author_id in processed_users or db.execute("SELECT 1 FROM seen_mentions WHERE id=?", (tweet_id,)).fetchone(): continue

                sys_msg = "أنت مستشار تقني خبير. أجب بعمق وقيمة. استخدم هاشتاق مناسب للرد."
                reply = await ask_ai(sys_msg, f"سؤال من @{author_id}: {t.text}", temperature=0.5)
                
                if reply:
                    client.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                    db.execute("INSERT INTO seen_mentions VALUES (?)", (tweet_id,))
                    db.commit()
                    processed_users.add(author_id)
                    logger.success(f"✅ تم الرد على @{author_id}")
                    await asyncio.sleep(5)
    except Exception as e: logger.error(f"❌ خطأ الردود: {e}")

# ================= 📅 SCHEDULED POST (النشر النوعي) =================
async def run_scheduled_post():
    today_date = datetime.now().strftime("%Y-%m-%d")
    today_name = datetime.now().strftime('%A')
    
    with sqlite3.connect("newsroom_v5.db") as db:
        if db.execute("SELECT 1 FROM daily_post WHERE date=?", (today_date,)).fetchone():
            logger.info("📅 تم النشر اليومي مسبقاً.")
            return

        if today_name == "Tuesday": # يوم البرومبتات
            sys, goal = "Prompt Engineer محترف.", "برومبت إنجليزي دقيق جداً (Prompt) لحل مشكلة فنية مع شرح إبداعي بالعربي."
        elif today_name == "Friday": # يوم المخططات
            sys, goal = "خبير أتمتة (Automation Architect).", "شرح مخطط ربط (Workflow) تقني للأفراد يزيد الإنتاجية بوضوح."
        else:
            sys, goal = "محلل تقني استقصائي.", "مقال تقني طويل (تحليل أو سبق صحفي) يركز على قيمة الأدوات للأفراد."

        content = await ask_ai(sys, f"اصنع محتوى دسم جداً لهذا اليوم: {goal}", temperature=0.8)
        if content:
            client.create_tweet(text=content)
            db.execute("INSERT INTO daily_post VALUES (?)", (today_date,))
            db.commit()
            logger.success(f"🔥 تم نشر محتوى {today_name} مع كامل الملحقات!")

# ================= 🚀 MAIN =================
async def main():
    init_db()
    # تنفيذ الردود أولاً لتعزيز التفاعل
    await handle_mentions()
    # تنفيذ النشر المجدول حسب استراتيجية الأيام
    await run_scheduled_post()

if __name__ == "__main__":
    asyncio.run(main())
