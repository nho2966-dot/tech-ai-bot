import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
import json
from datetime import datetime, timedelta, timezone
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_KEY"),
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
        db.execute("CREATE TABLE IF NOT EXISTS published (id INTEGER PRIMARY KEY, type TEXT, date TEXT)")
        # جدول لتتبع آخر تاريخ لنشر استطلاع
        db.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value TEXT)")
        db.commit()

# ================= 🧠 AI ENGINE =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=40) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.5,
                    "messages": [
                        {"role": "system", "content": system + "\n- لهجة خليجية بيضاء. احترافية. اختصار. ممنوع البتر."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"].strip() if res.status_code == 200 else None
    except: return None

# ================= 💬 MENTIONS (V13 PROTECTED) =================
async def handle_mentions():
    logger.info("🔍 فحص المنشنات الحديثة (فلترة 24 ساعة)...")
    try:
        me = client.get_me().data
        bot_id = str(me.id)
        mentions = client.get_users_mentions(id=bot_id, tweet_fields=['author_id', 'id', 'text', 'created_at'], max_results=15).data
        if not mentions: return

        threshold_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        processed_users = set()

        with sqlite3.connect("newsroom_v5.db") as db:
            for t in mentions:
                if t.created_at < threshold_24h or str(t.author_id) == bot_id: continue
                if db.execute("SELECT 1 FROM seen_mentions WHERE id=?", (str(t.id),)).fetchone(): continue
                if str(t.author_id) in processed_users: continue

                reply = await ask_ai("أنت مستشار تقني خبير. أجب بذكاء واختصار.", f"سؤال من @{t.author_id}: {t.text}")
                if reply:
                    client.create_tweet(text=reply[:275], in_reply_to_tweet_id=t.id)
                    db.execute("INSERT INTO seen_mentions VALUES (?)", (str(t.id),))
                    db.commit()
                    processed_users.add(str(t.author_id))
                    await asyncio.sleep(5)
    except Exception as e: logger.error(f"Mentions Error: {e}")

# ================= 📅 CONTENT STRATEGY (تنويع المحتوى) =================
async def run_strategic_content():
    init_db()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    with sqlite3.connect("newsroom_v5.db") as db:
        # 1. فحص هل تم النشر اليوم أصلاً؟ (لمنع التكرار)
        already_published = db.execute("SELECT 1 FROM published WHERE date=?", (today_date,)).fetchone()
        if already_published:
            logger.info("📅 تم النشر اليوم بالفعل. نكتفي بالردود.")
            return

        # 2. فحص متى كان آخر استطلاع؟ (نظام استطلاع واحد في الأسبوع)
        last_poll = db.execute("SELECT value FROM stats WHERE key='last_poll_date'").fetchone()
        can_post_poll = False
        if not last_poll:
            can_post_poll = True
        else:
            last_date = datetime.strptime(last_poll[0], "%Y-%m-%d")
            if (datetime.now() - last_date).days >= 7:
                can_post_poll = True

        # 3. اختيار نوع المحتوى لليوم
        content_type = "NEWS" # الافتراضي أخبار
        if can_post_poll and random.random() > 0.5: # إذا مر أسبوع، هناك فرصة لنشر استطلاع
            content_type = "POLL"
        elif random.random() > 0.7:
            content_type = "TIP" # نصيحة تقنية سريعة

        # تنفيذ النشر بناءً على النوع
        if content_type == "POLL":
            poll_q = random.choice([
                {"q": "وش أفضل AI Stack جربته لزيادة إنتاجيتك؟", "o": ["Claude + n8n", "GPT + Zapier", "Perplexity + Notion", "أدوات مخصصة"]},
                {"q": "في 2026، هل تعتقد أن تعلم 'هندسة الأوامر' لا يزال ضرورة؟", "o": ["نعم، أساسي جداً", "لا، الـ AI صار يفهمنا", "حسب التخصص", "مبكر الحكم"]}
            ])
            tw = client.create_tweet(text=poll_q["q"], poll_options=poll_q["o"], poll_duration_minutes=1440)
            db.execute("INSERT OR REPLACE INTO stats VALUES ('last_poll_date', ?)", (today_date,))
            logger.success("📊 تم نشر استطلاع الأسبوع.")

        elif content_type == "TIP":
            tip = await ask_ai("أنت خبير تقني.", "أعط نصيحة تقنية ذهبية قصيرة جداً لمتابعين مهتمين بالإنتاجية والذكاء الاصطناعي.")
            if tip: client.create_tweet(text=f"💡 نصيحة اليوم:\n\n{tip}")
            logger.success("💡 تم نشر نصيحة تقنية.")

        else: # أخبار (NEWS)
            # استدعاء دالة البحث والنشر Tavily كما هي في النسخ السابقة
            logger.info("🕵️ جاري البحث عن أخبار تقنية لنشرها...")
            # (هنا تضع منطق البحث في Tavily والنشر كثريد)

        # تسجيل أنه تم النشر اليوم
        db.execute("INSERT INTO published (type, date) VALUES (?, ?)", (content_type, today_date))
        db.commit()

# ================= 🚀 MAIN =================
async def main():
    init_db()
    # الردود دائماً فعالة للرد على المنشنات الحديثة
    await handle_mentions()
    
    # إدارة المحتوى الاستراتيجي (استطلاع أسبوعي + تنويع)
    await run_strategic_content()

if __name__ == "__main__":
    asyncio.run(main())
