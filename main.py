import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
from datetime import datetime, timedelta, timezone
from loguru import logger
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# ================= 🔐 الإعدادات (CONFIG) =================
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

# إعداد عميل تويتر (V2)
client = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗂 قاعدة البيانات (DATABASE) =================
def init_db():
    with sqlite3.connect("newsroom_v5.db") as db:
        db.execute("""CREATE TABLE IF NOT EXISTS published (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, content TEXT, category TEXT, sources TEXT, 
            published_at TEXT, engagement_score INTEGER DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS tweets_metrics (
            tweet_id TEXT PRIMARY KEY, likes INTEGER, retweets INTEGER, 
            replies INTEGER, thread_id INTEGER)""")
        db.execute("CREATE TABLE IF NOT EXISTS seen_mentions (id TEXT PRIMARY KEY)")
        db.execute("""CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT PRIMARY KEY, last_topic TEXT, interaction_count INTEGER DEFAULT 1)""")
        db.commit()

# ================= 🧠 محرك الذكاء الاصطناعي (AI ENGINE) =================
async def ask_ai(system, prompt, temp=0.25):
    """محرك AI مع نظام إعادة المحاولة لضمان استقرار الاتصال"""
    strict_rules = "\n- لا تتجاوز 220 حرفاً. انهِ جملك دائماً. ممنوع بتر النص. لهجة خليجية بيضاء رصينة."
    for attempt in range(3): # محاولة لثلاث مرات في حال فشل الشبكة
        try:
            async with httpx.AsyncClient(timeout=60) as client_http:
                res = await client_http.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "temperature": temp,
                        "messages": [
                            {"role": "system", "content": system + strict_rules},
                            {"role": "user", "content": prompt}
                        ]
                    }
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"⚠️ محاولة AI رقم {attempt+1} تعثرت: {e}. جاري الإعادة...")
            await asyncio.sleep(5)
    return None

# ================= 💬 نظام الردود الذكي (MENTIONS) =================
async def handle_mentions():
    logger.info("🔍 فحص المنشنات بأسلوب التقدير والتحليل...")
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(
            id=me.id, 
            tweet_fields=['created_at', 'author_id', 'text'],
            expansions=['author_id']
        ).data
        
        if not mentions:
            logger.info("✅ لا توجد منشنات جديدة.")
            return

        with sqlite3.connect("newsroom_v5.db") as db:
            threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            for t in mentions:
                if t.created_at < threshold: continue
                if db.execute("SELECT 1 FROM seen_mentions WHERE id=?", (str(t.id),)).fetchone(): continue
                if str(t.author_id) == str(me.id): continue
                
                user = db.execute("SELECT last_topic, interaction_count FROM user_memory WHERE user_id=?", (str(t.author_id),)).fetchone()
                
                sys_msg = """أنت مستشار تقني خليجي ذكي. 
                - ابدأ بتقدير رأي المغرد (مثلاً: كلام في محله، إضافة ذكية، نظرة ثاقبة).
                - أضف تحليلاً تقنياً مختصراً جداً.
                - لا تبتر الجمل واجعل الرد يبدو بشرياً."""

                reply = await ask_ai(sys_msg, f"المغرد يقول: {t.text}")
                
                if reply:
                    client.create_tweet(text=reply[:275], in_reply_to_tweet_id=t.id)
                    db.execute("INSERT INTO seen_mentions VALUES (?)", (str(t.id),))
                    db.execute("""INSERT INTO user_memory (user_id, last_topic, interaction_count) 
                                  VALUES (?, ?, 1) ON CONFLICT(user_id) 
                                  DO UPDATE SET interaction_count=interaction_count+1, last_topic=?""", 
                               (str(t.author_id), t.text[:50], t.text[:50]))
                    db.commit()
                    logger.success(f"✅ تم الرد التحليلي على: {t.author_id}")
                    await asyncio.sleep(random.randint(5, 10))
    except Exception as e:
        logger.error(f"❌ خطأ في الردود: {e}")

# ================= 📝 محرك النشر الصحفي (NEWSROOM) =================
async def run_newsroom():
    logger.info("🕵️ البحث عن سبق صحفي تقني...")
    time_limit = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    query = "latest leaked AI tools for individuals productivity March 2026"
    
    try:
        async with httpx.AsyncClient(timeout=40) as client_http:
            res = await client_http.post("https://api.tavily.com/search",
                json={"api_key": CONF["TAVILY"], "query": query, "search_depth": "advanced", "max_results": 3})
            
            if res.status_code != 200:
                logger.error(f"❌ خطأ Tavily: {res.status_code}")
                return
            news_list = res.json().get("results", [])

        for item in news_list[:1]:
            title = item["title"]
            with sqlite3.connect("newsroom_v5.db") as db:
                if db.execute("SELECT 1 FROM published WHERE title=?", (title,)).fetchone(): continue
            
            sys_msg = "أنت محرر تقني خليجي. صغ ثريد من 3 تغريدات مشوقة للأفراد. لا تبتر النصوص."
            content = await ask_ai(sys_msg, f"الخبر: {title}\nالتفاصيل: {item['content']}")
            
            if content:
                tweets = [t.strip() for t in content.split("\n\n") if len(t.strip()) > 10]
                prev_id = None
                with sqlite3.connect("newsroom_v5.db") as db:
                    cursor = db.execute("INSERT INTO published (title, content, published_at) VALUES (?,?,?)", 
                                        (title, content, datetime.now().isoformat()))
                    thread_db_id = cursor.lastrowid
                    
                    for i, tweet_text in enumerate(tweets):
                        final_text = tweet_text
                        if i == len(tweets) - 1: final_text += "\n\nوش رأيكم بهالتطور؟ 👇"
                        
                        try:
                            tw = client.create_tweet(text=final_text[:280], in_reply_to_tweet_id=prev_id)
                            prev_id = tw.data["id"]
                            db.execute("INSERT INTO tweets_metrics VALUES (?,0,0,0,?)", (prev_id, thread_db_id))
                            await asyncio.sleep(5)
                        except Exception as e:
                            logger.error(f"❌ فشل نشر تغريدة: {e}")
                            break 
                    db.commit()
                logger.success(f"🔥 تم نشر ثريد بنجاح: {title}")
    except Exception as e:
        logger.error(f"❌ خطأ عام في النشر: {e}")

# ================= 🚀 المحرك الرئيسي (MAIN) =================
async def main():
    init_db()
    await handle_mentions()
    
    wait_time = random.randint(300, 600) # استراحة بين 5-10 دقائق
    logger.info(f"☕ استراحة محارب لمدة {wait_time // 60} دقيقة...")
    await asyncio.sleep(wait_time)
    
    await run_newsroom()
    logger.info("🏁 انتهت الجولة بنجاح.")

if __name__ == "__main__":
    asyncio.run(main())
