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

load_dotenv()

# ================= CONFIG =================
GROQ = os.getenv("GROQ_API_KEY")
TAVILY = os.getenv("TAVILY_API_KEY")

twitter = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

# ================= MEMORY =================
db = sqlite3.connect("v200_memory.db")
db.execute("CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY, topic TEXT UNIQUE)")
db.execute("CREATE TABLE IF NOT EXISTS replies(id TEXT PRIMARY KEY)")
db.commit()

dimension = 384
index = faiss.IndexFlatL2(dimension)
memory_text = []

def embed(text):
    return np.random.rand(dimension).astype("float32")

def save_vector(text):
    vec = embed(text)
    index.add(np.array([vec]))
    memory_text.append(text)

def is_similar(text):
    if index.ntotal == 0:
        return False
    D, I = index.search(np.array([embed(text)]), 1)
    return D[0][0] < 0.3

# ================= CLEANING =================
def clean(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#-]', '', text)
    text = re.sub(r'^\d+[:/]\s*', '', text)
    text = " ".join(text.split())
    return text

# ================= AI CALL =================
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

# ================= TREND DISCOVERY =================
async def discover_topic():
    past_topics = [row[0] for row in db.execute("SELECT topic FROM topics").fetchall()]
    past_context = f"تجنب تماماً: {', '.join(past_topics[-15:])}" if past_topics else ""
    system = "أنت خبير تقني للأفراد، تكتشف أسرار التقنية غير المعروفة."
    prompt = f"اقترح سر تقني جديد لعام 2026 للأفراد. {past_context}"
    topic = await ask_ai(system, prompt)
    if topic and not is_similar(topic):
        db.execute("INSERT INTO topics(topic) VALUES(?)", (topic,))
        db.commit()
        save_vector(topic)
        return topic
    return None

# ================= RESEARCH =================
async def research(topic):
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={
            "api_key": TAVILY,
            "query": f"precise technical hidden hack for {topic} 2026",
            "search_depth": "advanced"
        })
        return "\n".join([x["content"] for x in r.json().get("results", [])])

# ================= THREAD GENERATION =================
async def generate_thread(topic, knowledge):
    system = "أنت Senior Solution Architect، اكتب Thread للأفراد 2026."
    prompt = f"""
الموضوع: {topic}
المعلومات: {knowledge}
أكتب 4–6 تغريدات واضحة، مباشرة، عملية.
التغريدة الأولى: السر مباشرة.
البقية: خطوات التنفيذ.
ممنوع الحشو، لغة الإعلانات، ورموز غير عربية.
"""
    raw = await ask_ai(system, prompt)
    tweets = [clean(t) for t in re.split(r'\n\n|\d+[:/]\s*', raw) if len(t)>20]
    return tweets[:6]

# ================= QUALITY REVIEW =================
async def quality_check(thread):
    system = "أنت محرر محتوى تقني، قيم الجودة والعمق."
    prompt = f"""
قيم هذا Thread من 1-10 على:
- technical depth
- clarity
- virality
{thread}
"""
    score = await ask_ai(system, prompt)
    return score

# ================= POST THREAD =================
async def post_thread(tweets):
    prev_id = None
    for i, t in enumerate(tweets):
        try:
            full_text = f"{i+1}/ {t}"[:270]
            if prev_id is None:
                res = twitter.create_tweet(text=full_text)
            else:
                res = twitter.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(12)
        except Exception as e:
            logger.error(e)

# ================= SMART REPLY =================
async def smart_reply():
    me = twitter.get_me()
    mentions = twitter.get_users_mentions(id=me.data.id)
    if not mentions.data: return
    for tweet in mentions.data:
        if db.execute("SELECT id FROM replies WHERE id=?", (tweet.id,)).fetchone(): continue
        system = "أنت Senior Solution Architect، رد على الأسئلة التقنية بدقة."
        answer = await ask_ai(system, tweet.text)
        if answer:
            twitter.create_tweet(text=clean(answer), in_reply_to_tweet_id=tweet.id)
            db.execute("INSERT INTO replies(id) VALUES(?)",(tweet.id,))
            db.commit()

# ================= DAILY MISSION =================
async def daily_mission():
    topic = await discover_topic()
    if not topic: return
    knowledge = await research(topic)
    thread = await generate_thread(topic, knowledge)
    score = await quality_check(thread)
    logger.info(f"Thread score: {score}")
    await post_thread(thread)

# ================= MAIN LOOP =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V200 Full Automation Online | Mode: {mode}")

    # Start the scheduler inside the running event loop
    scheduler = AsyncIOScheduler()
    if mode != "manual":
        scheduler.add_job(daily_mission, "cron", hour=10)
        scheduler.add_job(smart_reply, "cron", hour=19)
        scheduler.start()

    # Manual mode runs tasks immediately
    if mode == "manual":
        await daily_mission()
        await smart_reply()
        return

    # Keep the loop alive in auto mode
    while True:
        await asyncio.sleep(3600)

# ================= ENTRY POINT =================
if __name__ == "__main__":
    mode = "manual" if (len(sys.argv)>1 and sys.argv[1]=="manual") else "auto"
    asyncio.run(main_loop(mode))
