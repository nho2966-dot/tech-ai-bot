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

# حسابات مستهدفة للاشتباك التقني (أضف من تريد هنا)
TARGET_ACCOUNTS = ["OpenAI", "ylecun", "karpathy", "sama", "GoogleDeepMind"]

twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🗄️ MEMORY DB =================
db = sqlite3.connect("tech_sovereignty_v160.db")
db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY)")
db.commit()

def is_seen(uid):
    return db.execute("SELECT id FROM memory WHERE id=?", (uid,)).fetchone() is not None

def save_seen(uid):
    db.execute("INSERT INTO memory (id) VALUES (?)", (uid,))
    db.commit()

# ================= 🛡️ THE GHOST FILTER (منع الحشو والهلوسة) =================
def clean_and_verify(text):
    # حذف الرموز الغريبة والرموز التعبيرية المبالغ فيها
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:/]', '', text)
    
    # قائمة الكلمات المحظورة (الحشو والهلوسة)
    forbidden = ["في هذا المنشور", "أهلاً بكم", "يسعدني", "لا تتردد", "شكراً لمتابعتكم", "عزيزي القارئ"]
    for word in forbidden:
        text = text.replace(word, "")
    
    # توزيع الأسطر هندسياً (Scannable)
    text = text.replace(". ", ".\n\n")
    return " ".join(text.split()).replace(".\n\n ", ".\n\n").strip()

# ================= 🧠 AI BRAIN (Zero-Tolerance for Fluff) =================
async def ask_ai(system, prompt, temp=0.2): # حرارة منخفضة جداً لمنع الهلوسة
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": temp,
                    "messages": [
                        {"role": "system", "content": system + "\n- ممنوع الحشو.\n- ممنوع المقدمات.\n- ادخل في صلب الـ Architecture."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= ⚔️ ENGAGEMENT (الاشتباك التقني) =================
async def engage_with_giants():
    logger.info("⚔️ جاري البحث عن أهداف للاشتباك التقني...")
    for account in TARGET_ACCOUNTS:
        try:
            user = twitter.get_user(username=account)
            tweets = twitter.get_users_tweets(id=user.data.id, max_results=5)
            if not tweets.data: continue

            for tweet in tweets.data:
                if is_seen(f"engage_{tweet.id}"): continue
                
                # تحليل التغريدة والرد عليها بنقاش هندسي
                sys_msg = "أنت Senior AI Engineer. حلل التغريدة ورد عليها بنقاش تقني عميق (Architecture/Optimization)."
                reply_content = await ask_ai(sys_msg, f"تغريدة {account}: {tweet.text}")
                
                if reply_content:
                    twitter.create_tweet(text=clean_and_verify(reply_content), in_reply_to_tweet_id=tweet.id)
                    save_seen(f"engage_{tweet.id}")
                    logger.success(f"✅ تم الاشتباك مع {account}")
                    break # رد واحد لكل حساب في الدورة الواحدة
        except Exception as e:
            logger.error(f"Engage Error: {e}")

# ================= 🧵 DAILY MISSION (High Density) =================
async def run_daily_mission():
    logger.info("🎯 توليد محتوى تقني عالي الكثافة...")
    topic_sys = "اقترح ترند تقني معقد (مثل LLM Quantization أو Distributed Training)."
    topic = await ask_ai(topic_sys, "عنوان هندسي دسم.")
    
    if not topic: return

    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": topic})
        knowledge = "\n".join([x["content"] for x in r.json().get("results", [])])

    thread_sys = """أنت CTO حاد الذكاء. 
    1. ابدأ بالمشكلة التقنية.
    2. اشرح الـ Stack (Frameworks/DBs).
    3. اذكر أرقام أو مقارنات (Latency/Throughput).
    4. ممنوع الحشو الإنشائي نهائياً."""
    
    raw_content = await ask_ai(thread_sys, f"الموضوع: {topic}\nالمعرفة: {knowledge}")
    
    # تقسيم ذكي للثريد
    tweets = [clean_and_verify(t) for t in re.split(r'\d+\s*[/-]\s*', raw_content) if len(t) > 30]
    
    prev_id = None
    for i, t in enumerate(tweets[:5]):
        res = twitter.create_tweet(text=f"{i+1}/ {t}", in_reply_to_tweet_id=prev_id)
        prev_id = res.data["id"]
        await asyncio.sleep(10)

# ================= 🚀 EXECUTION =================
async def main_loop(mode="auto"):
    logger.info(f"🚀 V160 Online | Mode: {mode}")
    
    if mode == "manual":
        await run_daily_mission()
        await engage_with_giants()
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_mission, 'cron', hour=10)
    scheduler.add_job(engage_with_giants, 'interval', hours=4)
    scheduler.add_job(lambda: logger.info("Checking Mentions..."), 'interval', minutes=15)
    
    scheduler.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    mode = "manual" if (len(sys.argv) > 1 and sys.argv[1] == "manual") else "auto"
    asyncio.run(main_loop(mode))
