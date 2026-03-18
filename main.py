import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
import random
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# ================= 🗄️ DATABASE SETUP =================
DB_NAME = "tech_database.db"
db = sqlite3.connect(DB_NAME)
db.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        tweet_id TEXT PRIMARY KEY, 
        author_id TEXT,
        type TEXT, 
        style TEXT, 
        hook TEXT, 
        likes INTEGER DEFAULT 0, 
        retweets INTEGER DEFAULT 0, 
        date TEXT
    )
""")
db.commit()

# ================= 🛡️ FILTERS & UTILS =================
def clean_pro(text):
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    text = re.sub(r'^\d+[/]\d+[:/-]*\s*', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#%-]', '', text)
    return " ".join(text.split()).strip()[:275]

def get_cooldown_hours(followers):
    if followers >= 1_000_000: return 6
    if followers >= 100_000: return 12
    if followers >= 10_000: return 24
    return 48

# ================= 🧠 BRAIN: STRATEGY & LEARNING =================
def get_best_strategy():
    try:
        res = db.execute("""
            SELECT style, hook FROM logs 
            WHERE likes > 2 
            ORDER BY (likes + (retweets * 2)) DESC LIMIT 1
        """).fetchone()
        return {"style": res[0], "hook": res[1]} if res else None
    except: return None

def get_recent_hooks():
    try:
        res = db.execute("SELECT hook FROM logs ORDER BY date DESC LIMIT 10").fetchall()
        return [r[0] for r in res if r[0]]
    except: return []

# ================= 🤖 AI ENGINE (AUTO-EVOLUTION) =================
async def ask_ai(prompt, mode="opinion"):
    strategy = get_best_strategy()
    recent_hooks = get_recent_hooks()
    
    current_style = strategy['style'] if strategy else "تحليلي ومستقبلي"
    
    system = f"""
    أنت خبير تقني Sniper في 2026. ردودك ذكية، مكثفة، وبدون حشو.
    [الهوية] صوتك واثق، رؤيتك استشرافية، تعطي توقعات دقيقة.
    [التطور الذاتي] أفضل أسلوب حقق نجاحاً لك هو: "{current_style}". تفوق عليه بذكاء.
    [قاعدة التنوع] ممنوع استخدام هذه الافتتاحيات: {", ".join(recent_hooks)}.
    [الوضع] {mode}. التاريخ: 2026.
    """
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.7,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🕵️ SMART SNIPER REPLY =================
async def smart_reply():
    logger.info("🕵️ فحص المنشنات للردود الذكية...")
    try:
        me = twitter.get_me(user_auth=True).data
        my_id = str(me.id)
        
        mentions = twitter.get_users_mentions(
            id=my_id, max_results=15, user_auth=True, 
            tweet_fields=['created_at', 'author_id', 'text'],
            expansions=['author_id'], user_fields=['public_metrics']
        )
        
        if not mentions or not mentions.data: 
            logger.info("⏳ لا توجد منشنات جديدة.")
            return

        users_map = {str(u.id): u.public_metrics['followers_count'] for u in mentions.includes['users']} if mentions.includes else {}

        for tweet in mentions.data:
            t_id = str(tweet.id)
            a_id = str(tweet.author_id)
            
            if a_id == my_id: continue
            
            followers = users_map.get(a_id, 0)
            cd_limit = (datetime.now(timezone.utc) - timedelta(hours=get_cooldown_hours(followers))).isoformat()
            
            # فحص الـ Cooldown
            if db.execute("SELECT tweet_id FROM logs WHERE author_id=? AND date > ?", (a_id, cd_limit)).fetchone():
                continue

            # صيد التغريدات الجديدة (Sniping < 15 min)
            if (datetime.now(timezone.utc) - tweet.created_at).total_seconds() > 900:
                continue

            mode = "educational" if any(x in tweet.text for x in ["كيف", "ليش", "وش"]) else "opinion"
            ans = await ask_ai(tweet.text, mode=mode)
            
            if ans and len(ans.split()) >= 6:
                final = clean_pro(ans)
                resp = twitter.create_tweet(text=final, in_reply_to_tweet_id=t_id, user_auth=True)
                
                db.execute("INSERT INTO logs (tweet_id, author_id, type, style, hook, date) VALUES (?, ?, ?, ?, ?, ?)",
                           (str(resp.data['id']), a_id, "reply", mode, final[:50], datetime.now().isoformat()))
                db.commit()
                logger.success(f"🎯 Sniped Tier {get_cooldown_hours(followers)}h | Account: {a_id}")
                await asyncio.sleep(random.randint(40, 90))

    except Exception as e: logger.error(f"Reply Error: {e}")

# ================= 📈 PERFORMANCE UPDATER =================
async def update_stats():
    logger.info("📊 تحديث إحصائيات الأداء...")
    try:
        time_limit = (datetime.now() - timedelta(days=2)).isoformat()
        rows = db.execute("SELECT tweet_id FROM logs WHERE type='reply' AND date > ?", (time_limit,)).fetchall()
        
        for (tid,) in rows:
            try:
                t = twitter.get_tweet(id=tid, tweet_fields=['public_metrics'], user_auth=True)
                if t and t.data:
                    m = t.data.public_metrics
                    db.execute("UPDATE logs SET likes=?, retweets=? WHERE tweet_id=?", (m['like_count'], m['retweet_count'], tid))
            except: pass
        db.commit()
        logger.info("✅ تم تحديث الأداء بنجاح.")
    except Exception as e: logger.error(f"Stats Error: {e}")

# ================= 🧵 MISSION (Threads) =================
async def run_mission():
    logger.info("📡 بدء مهمة البحث والنشر (Thread Mission)...")
    topic = random.choice(["روبوت Helix 02", "معالجات Maya 200", "Vision Pro 2026", "الخصوصية في 2026"])
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": f"{topic} technology future 2026"})
            knowledge = "\n".join([x['content'] for x in r.json().get("results", [])])

        content = await ask_ai(f"اكتب ثريد 3 تغريدات مشوقة عن: {knowledge}", mode="thread")
        if not content: return
        
        tweets = [t for t in re.split(r'\n\n|\n', content) if len(t) > 30]
        p_id = None
        for i, t in enumerate(tweets[:3]):
            msg = f"{i+1}/3: {clean_pro(t)}"
            res = twitter.create_tweet(text=msg, in_reply_to_tweet_id=p_id, user_auth=True)
            p_id = res.data["id"]
            await asyncio.sleep(random.randint(60, 120))
        logger.success(f"✅ تم نشر ثريد عن: {topic}")
    except Exception as e: logger.error(f"Mission Error: {e}")

# ================= 🏁 RUN =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 Sniper Engine Online | Mode: {mode}")
    
    if mode == "manual":
        await run_mission()
        await smart_reply()
        await update_stats()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_mission, 'cron', hour='10,22') 
    scheduler.add_job(smart_reply, 'interval', minutes=15) 
    scheduler.add_job(update_stats, 'interval', hours=3)   
    
    scheduler.start()
    while True: 
        await asyncio.sleep(3600)

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "auto"
    try:
        asyncio.run(main_loop(mode=arg))
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 تم إيقاف النظام.")
