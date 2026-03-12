import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
from loguru import logger
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

# ================= 🐦 Twitter Clients =================
# Client للقراءة (Bearer Token) لتجنب 401
twitter_read = tweepy.asynchronous.AsyncClient(
    bearer_token=CONF["X"]["bearer"],
    wait_on_rate_limit=True
)

# Client للنشر (مع كل المفاتيح)
twitter_write = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"],
    wait_on_rate_limit=True
)

# ================= 🗄️ MEMORY =================
db = sqlite3.connect("tech_secrets_v250.db")
db.execute("CREATE TABLE IF NOT EXISTS topics (topic TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY)")
db.commit()

def get_past_topics():
    cursor = db.execute("SELECT topic FROM topics")
    return [row[0] for row in cursor.fetchall()][-15:]

def save_topic(topic):
    db.execute("INSERT INTO topics (topic) VALUES (?)", (topic,))
    db.commit()

def is_duplicate(entry_id):
    check = db.execute("SELECT id FROM memory WHERE id=?", (entry_id,)).fetchone()
    return check is not None

def save_to_memory(entry_id):
    db.execute("INSERT INTO memory (id) VALUES (?)", (entry_id,))
    db.commit()

# ================= 🛡️ CLEANER =================
def clean_text(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#-]', '', text)
    text = " ".join(text.split())
    return text

# ================= 🧠 AI ENGINE =================
async def ask_ai(system, prompt, temp=0.4):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- اللهجة: خليجية تقنية حادة."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🐦 Twitter Helpers =================
async def fetch_recent_tweets(username, limit=5):
    try:
        user = await twitter_read.get_user(username=username)
        user_id = user.data.id
        tweets = await twitter_read.get_users_tweets(id=user_id, max_results=limit)
        if tweets.data:
            return [t.text for t in tweets.data]
        return []
    except Exception as e:
        logger.error(f"Error fetching tweets: {e}")
        return []

async def fetch_mentions():
    try:
        me = await twitter_read.get_me()
        mentions = await twitter_read.get_users_mentions(id=me.data.id, max_results=5)
        if mentions.data:
            return [t.text for t in mentions.data]
        return []
    except Exception as e:
        logger.error(f"Error fetching mentions: {e}")
        return []

# ================= 🧵 THREAD BUILDER =================
async def build_insight_thread(username):
    tweets = await fetch_recent_tweets(username)
    if not tweets:
        logger.warning("لا توجد تغريدات لتحليلها.")
        return []
    knowledge = "\n".join(tweets)
    system = "أنت Senior Solution Architect. حول التغريدات التقنية إلى Thread غني بالمعلومات، مع خطوات عملية وأدوات محددة."
    raw_thread = await ask_ai(system, knowledge)
    if raw_thread:
        return [clean_text(t) for t in re.split(r'\n\n', raw_thread) if len(t) > 20]
    return []

async def post_thread(tweets):
    prev_id = None
    for i, tweet in enumerate(tweets):
        text = f"{i+1}/ {tweet}"
        try:
            if prev_id is None:
                res = twitter_write.create_tweet(text=text)
            else:
                res = twitter_write.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(4)
        except Exception as e:
            logger.error(f"Error posting tweet {i+1}: {e}")

# ================= 🔍 ANALYZE COMPETITORS =================
async def analyze_competitors():
    logger.info("📡 رادار المنافسين يعمل...")
    targets = ["OpenAI", "Anthropic", "karpathy", "ylecun"]
    for target in targets:
        try:
            tweets = await fetch_recent_tweets(target, limit=1)
            if not tweets: continue
            latest = tweets[0]
            if is_duplicate(f"roast_{target}"): continue
            system = "أنت CTO متمرد. انتقد هذا الطرح السطحي بعمق تقني (Architecture, Latency, Cost)."
            response = await ask_ai(system, latest)
            if response:
                twitter_write.create_tweet(text=clean_text(response), in_reply_to_tweet_id=None)
                save_to_memory(f"roast_{target}")
        except Exception as e:
            logger.error(f"Error analyzing competitor {target}: {e}")

# ================= 🤖 SMART REPLY =================
async def smart_reply():
    mentions = await fetch_mentions()
    for mention in mentions:
        if is_duplicate(f"reply_{mention}"): continue
        system = "أنت Senior Solution Architect. رد على السؤال التقني بوضوح وعمق."
        answer = await ask_ai(system, mention)
        if answer:
            twitter_write.create_tweet(text=clean_text(answer))
            save_to_memory(f"reply_{mention}")

# ================= 🚀 DAILY MISSION =================
async def daily_mission(username="X_TechNews_"):
    logger.info(f"🔍 تحليل ونشر Thread من @{username}")
    thread = await build_insight_thread(username)
    if thread:
        await post_thread(thread)

# ================= 🏁 MAIN LOOP =================
async def main_loop(username="X_TechNews_", mode="auto"):
    logger.info(f"🚀 V250 Full Empire Online | Mode: {mode}")
    if mode == "manual":
        await daily_mission(username)
        await analyze_competitors()
        await smart_reply()
        return
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_mission, 'cron', hour=10, args=[username])
    scheduler.start()
    while True:
        await asyncio.sleep(3600)

# ================= 🏃 RUN =================
if __name__ == "__main__":
    mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode=mode))
