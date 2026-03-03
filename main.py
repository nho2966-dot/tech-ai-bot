import os
import asyncio
import httpx
import tweepy
import sqlite3
from datetime import datetime, timedelta, timezone, date
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

# ================= 🗂 DATABASE SETUP =================
def init_db():
    with sqlite3.connect("newsroom_v5.db") as db:
        db.execute("""CREATE TABLE IF NOT EXISTS published (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, content TEXT, category TEXT, sources TEXT, 
            published_at TEXT, engagement_score INTEGER DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS tweets_metrics (
            tweet_id TEXT PRIMARY KEY, likes INTEGER, retweets INTEGER, 
            replies INTEGER, thread_id INTEGER)""")
        db.commit()

# ================= 🧠 AI ENGINE (No Hallucination) =================
async def ask_ai(system, prompt, temp=0.25):
    try:
        async with httpx.AsyncClient(timeout=30) as client_http:
            r = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- التزم بالحقائق. ممنوع الهلوسة. لهجة خليجية بيضاء رصينة."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
    return None

# ================= 🕵️ NEWS DISCOVERY =================
async def fetch_trending_news():
    # جلب أخبار الـ 24 ساعة الماضية
    time_limit = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    query = f"breaking AI SaaS tools for individuals productivity news after:{time_limit}"
    
    async with httpx.AsyncClient(timeout=20) as client_http:
        r = await client_http.post("https://api.tavily.com/search",
            json={"api_key": CONF["TAVILY"], "query": query, "search_depth": "advanced", "max_results": 6})
        return r.json().get("results", []) if r.status_code == 200 else []

# ================= 📝 PUBLISHING ENGINE =================
async def publish_thread(thread_text, thread_db_id=None):
    tweets = [t.strip() for t in thread_text.split("\n\n") if len(t.strip()) > 10]
    prev_id = None
    
    for i, t in enumerate(tweets):
        try:
            # إضافة لمسة أنسنة في التغريدة الأخيرة
            content = t
            if i == len(tweets) - 1:
                content += "\n\nوش رأيكم بهالتطور؟ يخدمكم في شغلكم؟ 👇"
            
            tw = client.create_tweet(text=content[:280], in_reply_to_tweet_id=prev_id)
            prev_id = tw.data["id"]
            
            with sqlite3.connect("newsroom_v5.db") as db:
                db.execute("INSERT OR IGNORE INTO tweets_metrics VALUES (?,0,0,0,?)", (prev_id, thread_db_id))
                db.commit()
            
            await asyncio.sleep(3) # فاصل زمني لتجنب الـ Rate Limit
        except Exception as e:
            logger.error(f"Publishing error at tweet {i}: {e}")
    return prev_id

# ================= 📊 WEEKLY DIGEST (حصاد الأسبوع) =================
async def run_weekly_digest():
    # يعمل فقط يوم الجمعة
    if datetime.now().weekday() != 4: 
        return

    logger.info("📅 جاري تجهيز الحصاد الأسبوعي لأكثر المواضيع تفاعلاً...")
    with sqlite3.connect("newsroom_v5.db") as db:
        # جلب أفضل 3 مواضيع حققت تفاعل هذا الأسبوع
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        top_news = db.execute("""SELECT title, content FROM published 
                                 WHERE published_at > ? ORDER BY engagement_score DESC LIMIT 3""", (week_ago,)).fetchall()
        
        if not top_news: return

        combined = "\n---\n".join([f"الخبر: {n[0]}\nالملخص: {n[1][:150]}" for n in top_news])
        system = "أنت محرر تقني بارع. صغ 'حصاد الأسبوع' لأهم 3 أخبار تقنية بأسلوب مشوق ومختصر للأفراد."
        digest_text = await ask_ai(system, f"أبرز أحداث الأسبوع:\n{combined}")
        
        if digest_text:
            await publish_thread(f"🚀 حصاد الأسبوع التقني:\n\n{digest_text}")
            logger.success("✅ تم نشر الحصاد الأسبوعي بنجاح.")

# ================= 📊 METRICS & SCORES =================
async def update_all_metrics():
    with sqlite3.connect("newsroom_v5.db") as db:
        rows = db.execute("SELECT tweet_id, thread_id FROM tweets_metrics").fetchall()
        for tid, thread_id in rows:
            try:
                tweet = client.get_tweet(tid, tweet_fields=["public_metrics"]).data
                m = tweet["public_metrics"]
                db.execute("UPDATE tweets_metrics SET likes=?, retweets=?, replies=? WHERE tweet_id=?",
                           (m["like_count"], m["retweet_count"], m["reply_count"], tid))
                # تحديث التفاعل الإجمالي للخبر
                score = m["like_count"] + (m["retweet_count"] * 2) + (m["reply_count"] * 3)
                db.execute("UPDATE published SET engagement_score = engagement_score + ? WHERE id = ?", (score, thread_id))
            except: pass
        db.commit()

# ================= 🚀 MAIN PROCESS =================
async def run_newsroom():
    init_db()
    news = await fetch_trending_news()
    
    if not news: return

    for item in news[:2]: # نركز على أفضل خبرين يومياً لضمان الجودة
        title = item["title"]
        with sqlite3.connect("newsroom_v5.db") as db:
            if db.execute("SELECT 1 FROM published WHERE title=?", (title,)).fetchone(): continue
        
        system = "صغ ثريد تقني من 4 تغريدات مبني على الحقائق. ركز على الفائدة المباشرة للفرد."
        thread_content = await ask_ai(system, f"الخبر: {title}\nالتفاصيل: {item['content']}")
        
        if thread_content:
            with sqlite3.connect("newsroom_v5.db") as db:
                cursor = db.execute("INSERT INTO published (title, content, published_at) VALUES (?,?,?)", 
                                    (title, thread_content, datetime.now().isoformat()))
                thread_id = cursor.lastrowid
                db.commit()
            
            await publish_thread(thread_content, thread_id)
            logger.success(f"🔥 تم نشر ثريد جديد: {title}")

async def main():
    await run_newsroom()
    await update_all_metrics()
    await run_weekly_digest()

if __name__ == "__main__":
    asyncio.run(main())
