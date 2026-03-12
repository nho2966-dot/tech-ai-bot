import os
import re
import sys
import asyncio
import httpx
import tweepy
import sqlite3
import numpy as np
import faiss
from loguru import logger
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ===================== CONFIG =====================
load_dotenv()

GROQ = os.getenv("GROQ_API_KEY")
TAVILY = os.getenv("TAVILY_API_KEY")

twitter = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

# ===================== DATABASE =====================
db = sqlite3.connect("v250_memory.db")
db.execute("CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY, topic TEXT UNIQUE)")
db.execute("CREATE TABLE IF NOT EXISTS replies(id TEXT PRIMARY KEY)")
db.commit()

# ===================== VECTOR MEMORY =====================
dimension = 384
index = faiss.IndexFlatL2(dimension)
memory_text = []

def embed(text):
    return np.random.rand(dimension).astype("float32")  # استبدلها بوظيفة embedding حقيقية إذا أردت

def save_vector(text):
    vec = embed(text)
    index.add(np.array([vec]))
    memory_text.append(text)

def is_similar(text):
    if index.ntotal == 0:
        return False
    D, I = index.search(np.array([embed(text)]), 1)
    return D[0][0] < 0.3

# ===================== CLEANING =====================
def clean(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#-]', '', text)
    text = re.sub(r'^\d+[:/]\s*', '', text)
    return " ".join(text.split())

# ===================== AI CALL =====================
async def ask_ai(system, prompt, temp=0.3):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages":[
                        {"role":"system","content":system},
                        {"role":"user","content":prompt}
                    ]
                }
            )
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ===================== FETCH X TWEETS =====================
async def fetch_recent_tweets(username, limit=10):
    user = twitter.get_user(username=username)
    tweets = twitter.get_users_tweets(id=user.data.id, max_results=limit)
    return [t.text for t in tweets.data] if tweets.data else []

# ===================== ANALYZE TWEET DEEPLY =====================
async def analyze_tweet_deeply(tweet):
    system = """
أنت Senior Tech Analyst & Solution Architect
- اقرأ التغريدة وفسر معناها التقني بدقة.
- استخرج: الفكرة الرئيسية، التقنية المستخدمة، الفائدة العملية، المخاطر، الفرص المستقبلية.
- اعطِ خلاصة مختصرة قابلة للنشر كThread.
"""
    return await ask_ai(system, tweet, temp=0.3)

# ===================== THREAD BUILDER =====================
async def build_insight_thread(username):
    tweets = await fetch_recent_tweets(username, limit=5)
    thread = []
    for i, t in enumerate(tweets):
        if db.execute("SELECT id FROM replies WHERE id=?", (t,)).fetchone(): continue
        analysis = await analyze_tweet_deeply(t)
        cleaned = clean(analysis)
        if not is_similar(cleaned):  # لا تكرر المحتوى
            thread.append(f"{i+1}/ {cleaned}")
            save_vector(cleaned)
            db.execute("INSERT INTO replies(id) VALUES(?)", (t,))
            db.commit()
    return thread

# ===================== THREAD QUALITY CHECK =====================
async def quality_check(thread):
    system = """
أنت محرر محتوى تقني متمكن.
قيم هذا Thread على العمق التقني والوضوح وإمكانية الانتشار.
اعطِ درجة من 1-10 لكل معيار.
"""
    score = await ask_ai(system, "\n".join(thread))
    return score

# ===================== POST THREAD WITH RETRY =====================
async def post_thread(thread):
    prev_id = None
    for t in thread:
        for attempt in range(3):
            try:
                full_text = t[:270]
                if prev_id is None:
                    res = twitter.create_tweet(text=full_text)
                else:
                    res = twitter.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
                prev_id = res.data["id"]
                await asyncio.sleep(8)
                break
            except Exception as e:
                logger.warning(f"Retry {attempt+1} for tweet failed: {e}")
                await asyncio.sleep(5)

# ===================== SMART REPLY =====================
async def smart_reply():
    me = twitter.get_me()
    mentions = twitter.get_users_mentions(id=me.data.id)
    if not mentions.data: return
    for tweet in mentions.data:
        if db.execute("SELECT id FROM replies WHERE id=?", (tweet.id,)).fetchone(): continue
        system = "أنت Senior Solution Architect، رد على السؤال التقني بدقة وعملية."
        answer = await ask_ai(system, tweet.text)
        if answer:
            twitter.create_tweet(text=clean(answer), in_reply_to_tweet_id=tweet.id)
            db.execute("INSERT INTO replies(id) VALUES(?)",(tweet.id,))
            db.commit()

# ===================== DAILY MISSION =====================
async def daily_mission(username):
    thread = await build_insight_thread(username)
    if not thread: return
    score = await quality_check(thread)
    logger.info(f"Thread quality score:\n{score}")
    await post_thread(thread)

# ===================== MAIN LOOP =====================
async def main_loop(username, mode="auto"):
    logger.info(f"🚀 V250 Full Automation Online | Mode: {mode}")
    scheduler = AsyncIOScheduler()
    if mode != "manual":
        scheduler.add_job(lambda: daily_mission(username), "cron", hour=10)
        scheduler.add_job(smart_reply, "cron", hour=19)
        scheduler.start()
    if mode == "manual":
        await daily_mission(username)
        await smart_reply()
        return
    while True:
        await asyncio.sleep(3600)

# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    username = "X_TechNews_"  # الحساب الذي تريد تحليل تغريداته
    mode = "manual" if (len(sys.argv)>1 and sys.argv[1]=="manual") else "auto"
    asyncio.run(main_loop(username, mode))
