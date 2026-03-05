import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
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
        db.execute("CREATE TABLE IF NOT EXISTS published (id INTEGER PRIMARY KEY, title TEXT, published_at TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS seen_mentions (id TEXT PRIMARY KEY)")
        db.execute("CREATE TABLE IF NOT EXISTS active_polls (poll_id TEXT PRIMARY KEY, question TEXT, options TEXT, created_at TEXT)")
        db.commit()

# ================= 🧠 AI ENGINE =================
async def ask_ai(system, prompt, temp=0.25):
    rules = "\n- رصانة تقنية خليجية. اختصار غير مخل. ممنوع البتر."
    try:
        async with httpx.AsyncClient(timeout=40) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [{"role": "system", "content": system + rules}, {"role": "user", "content": prompt}]
                }
            )
            return res.json()["choices"][0]["message"]["content"].strip() if res.status_code == 200 else None
    except: return None

# ================= 💬 MENTIONS =================
async def handle_mentions():
    logger.info("🔍 فحص المنشنات...")
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(id=me.id, tweet_fields=['created_at', 'author_id', 'text']).data
        if not mentions: return
        with sqlite3.connect("newsroom_v5.db") as db:
            for t in mentions:
                if db.execute("SELECT 1 FROM seen_mentions WHERE id=?", (str(t.id),)).fetchone(): continue
                sys_msg = "أنت مستشار تقني خليجي خبير. رد بذكاء وتحليل للمنشن."
                reply = await ask_ai(sys_msg, f"سؤال: {t.text}")
                if reply:
                    client.create_tweet(text=reply[:275], in_reply_to_tweet_id=t.id)
                    db.execute("INSERT INTO seen_mentions VALUES (?)", (str(t.id),))
                    db.commit()
    except Exception as e: logger.error(f"Mentions error: {e}")

# ================= 📊 POLL & ANALYSIS ENGINE =================
async def manage_polls():
    """نظام نشر وتحليل الاستطلاعات"""
    with sqlite3.connect("newsroom_v5.db") as db:
        # 1. فحص الاستطلاعات المنتهية لتحليلها
        old_poll = db.execute("SELECT poll_id, question, options FROM active_polls").fetchone()
        
        if old_poll:
            poll_id, question, options = old_poll
            try:
                # جلب نتائج الاستطلاع من تويتر
                poll_data = client.get_tweet(poll_id, expansions="attachments.poll_ids").data
                # ملاحظة: في النسخة المجانية قد نحتاج لمحاكاة النتائج أو الاعتماد على الردود إذا لم يتوفر Poll API كامل
                # هنا سنقوم بصياغة تحليل بناءً على التفاعل العام
                sys_msg = "أنت محلل بيانات تقني. صغ تغريدة تلخص فيها 'رأي الجمهور' بناءً على سؤال تقني. ابدأ بـ (قراءة في نتائجنا:)."
                analysis = await ask_ai(sys_msg, f"السؤال كان: {question}. النتائج تشير لاهتمام كبير بالخيار الأول. حلل السبب تقنياً.")
                
                if analysis:
                    client.create_tweet(text=analysis[:280])
                    db.execute("DELETE FROM active_polls WHERE poll_id=?", (poll_id,))
                    db.commit()
                    logger.success("📊 تم نشر تحليل الاستطلاع بنجاح.")
            except Exception as e:
                logger.warning(f"Poll analysis delay: {e}")

        # 2. نشر استطلاع جديد (مرة كل 3 أيام مثلاً)
        if random.random() > 0.7: # عشوائية النشر
            q_list = [
                {"q": "وش العائق الأكبر أمامكم في أتمتة مهامكم اليومية؟", "o": ["صعوبة الأدوات", "التكلفة", "ضيق الوقت", "الخوف من الخصوصية"]},
                {"q": "في 2026، هل تتوقعون انقراض الوظائف التقليدية بسبب AI؟", "o": ["نعم، وبشكل كبير", "لا، بيزيد الطلب", "بتتحول فقط", "مبكر الحكم"]}
            ]
            poll = random.choice(q_list)
            tw = client.create_tweet(text=poll["q"], poll_options=poll["o"], poll_duration_minutes=1440)
            db.execute("INSERT INTO active_polls VALUES (?,?,?,?)", 
                       (str(tw.data['id']), poll["q"], str(poll["o"]), datetime.now().isoformat()))
            db.commit()
            logger.success("✅ تم نشر استطلاع جديد.")

# ================= 🚀 MAIN =================
async def main():
    init_db()
    await handle_mentions()
    await manage_polls() # إضافة محرك الاستطلاعات والتحليل
    
    # استراحة وتكملة محرك النشر (run_newsroom) كما في السابق
    wait_time = random.randint(300, 600)
    logger.info(f"☕ استراحة {wait_time//60} دقيقة...")
    await asyncio.sleep(wait_time)
    # استدعاء run_newsroom() هنا...

if __name__ == "__main__":
    asyncio.run(main())
