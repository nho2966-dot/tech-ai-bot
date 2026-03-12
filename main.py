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

# ================= 🗄️ MEMORY =================
db = sqlite3.connect("tech_empire_v250.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY)")
db.execute("CREATE TABLE IF NOT EXISTS topics (topic TEXT UNIQUE)")
db.commit()

def is_duplicate(entry_id):
    return db.execute("SELECT id FROM memory WHERE id=?", (entry_id,)).fetchone() is not None

def save_to_memory(entry_id):
    db.execute("INSERT OR IGNORE INTO memory (id) VALUES (?)", (entry_id,))
    db.commit()

def get_past_topics(limit=15):
    cursor = db.execute("SELECT topic FROM topics ORDER BY rowid DESC LIMIT ?", (limit,))
    return [row[0] for row in cursor.fetchall()]

def save_topic(topic):
    db.execute("INSERT OR IGNORE INTO topics (topic) VALUES (?)", (topic,))
    db.commit()

# ================= 🛡️ CLEAN CONTENT =================
def clean_and_verify(text):
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/#-]', '', text)
    garbage = ["يلا يا ناس", "لا تصدق؟", "جربوه وجيب لنا", "نراك في التغريدة التالية"]
    for word in garbage:
        text = text.replace(word, "")
    text = text.replace(". ", ".\n\n📍 ")
    return " ".join(text.split()).replace(".\n\n ", ".\n\n").strip()

# ================= 🧠 AI BRAIN =================
async def ask_ai(system, prompt, temp=0.3):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- اللهجة: خليجية بيضاء رصينة.\n- ممنوع استخدام أي لغة غير العربية.\n- ممنوع الترقيم (1:, 2:) داخل النص."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🐦 FETCH TWEETS =================
async def fetch_recent_tweets(username, limit=5):
    try:
        user = twitter.get_user(username=username)
        tweets = twitter.get_users_tweets(id=user.data.id, max_results=limit)
        return [t.text for t in tweets.data] if tweets.data else []
    except Exception as e:
        logger.error(f"Error fetching tweets: {e}")
        return []

# ================= 🧵 BUILD INSIGHT THREAD =================
async def build_insight_thread(username):
    tweets = await fetch_recent_tweets(username)
    if not tweets:
        logger.warning("لا توجد تغريدات لتحليلها.")
        return []

    system = "أنت خبير تحليل أخبار التقنية. استخرج الفائدة العملية، المخاطر، الأدوات، الخطوات، والملخص الاحترافي."
    prompt = "\n\n".join(tweets)
    raw_analysis = await ask_ai(system, prompt, temp=0.5)
    if not raw_analysis:
        return []

    steps = [clean_and_verify(s) for s in re.split(r'\n{1,2}', raw_analysis) if len(s) > 20]
    return steps[:6]

# ================= 🧵 POST THREAD =================
async def post_thread(tweets):
    prev_id = None
    for i, tweet in enumerate(tweets):
        try:
            full_text = f"{i+1}/ {tweet}"
            if prev_id is None:
                res = twitter.create_tweet(text=full_text)
            else:
                res = twitter.create_tweet(text=full_text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error posting tweet {i+1}: {e}")

# ================= 🕵️ COMPETITOR ANALYSIS =================
async def analyze_competitors(targets):
    logger.info("📡 رادار المنافسين يعمل...")
    for target in targets:
        try:
            user = twitter.get_user(username=target)
            tweets = twitter.get_users_tweets(id=user.data.id, max_results=3)
            if not tweets.data: continue

            latest = tweets.data[0]
            if is_duplicate(f"roast_{latest.id}"): continue

            system = "أنت CTO متمرد. انقد التغريدة التقنية بعمق (Architecture, Latency, Cost). اذكر ما فاتهم."
            response = await ask_ai(system, latest.text, temp=0.7)
            if response:
                twitter.create_tweet(text=clean_and_verify(response), in_reply_to_tweet_id=latest.id)
                save_to_memory(f"roast_{latest.id}")
                logger.success(f"🔥 تم تنفيذ الهيمنة على {target}")
        except Exception as e:
            logger.error(f"Error analyzing competitor {target}: {e}")

# ================= 🤖 SMART REPLY =================
async def smart_reply():
    logger.info("🔍 فحص المنشن للردود الذكية...")
    mentions = twitter.get_users_mentions(id=twitter.get_me().data.id)
    if not mentions.data: return

    for tweet in mentions.data:
        if is_duplicate(f"reply_{tweet.id}"): continue
        system = "أنت Senior Solution Architect. رد على السؤال التقني بوضوح وعمق. تجاهل المجاملات."
        answer = await ask_ai(system, tweet.text, temp=0.5)
        if answer:
            twitter.create_tweet(text=clean_and_verify(answer), in_reply_to_tweet_id=tweet.id)
            save_to_memory(f"reply_{tweet.id}")
            logger.success("✅ تم الرد الذكي!")

# ================= 🚀 DAILY MISSION =================
async def daily_mission(username):
    logger.info(f"🔍 تحليل ونشر Thread من @{username}")
    thread = await build_insight_thread(username)
    if thread:
        await post_thread(thread)
        logger.success(f"🔥 تم نشر Thread تحليل الخبر من @{username}")

# ================= 🚀 MAIN LOOP =================
async def main_loop(username, mode="auto"):
    logger.info(f"🚀 V250 Full Empire Online | Mode: {mode}")
    targets = ["OpenAI", "Anthropic", "karpathy", "ylecun"]

    if mode == "manual":
        await daily_mission(username)
        await analyze_competitors(targets)
        await smart_reply()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(daily_mission(username)), 'cron', hour=10)
    scheduler.add_job(lambda: asyncio.create_task(analyze_competitors(targets)), 'cron', hour=12)
    scheduler.add_job(lambda: asyncio.create_task(smart_reply()), 'cron', hour=14)
    scheduler.start()

    while True:
        await asyncio.sleep(3600)

# ================= 🏁 ENTRY POINT =================
if __name__ == "__main__":
    username = "X_TechNews_"
    mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(username, mode))
