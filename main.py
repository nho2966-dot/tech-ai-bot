import os
import re
import json
import time
import asyncio
import random
import sqlite3
import tweepy
import httpx
import telegram
from datetime import datetime
from loguru import logger
from google import genai
from openai import OpenAI
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ إعدادات عامة (Apex Radar & Telegram)
# ==========================================
MAX_POST_LENGTH = 24500
DB_FILE = "apex_engine.db"
BRAIN_STATS_FILE = "brain_stats.json"
CONTENT_STATS_FILE = "content_stats.json"
POST_INTERVAL = 21600      # كل 6 ساعات
INTERACTION_COUNT = 5       # عدد الردود بعد كل منشور
INTERACTION_GAP = 600      # فاصل 10 دقائق بين الردود

# مفاتيح API
KEYS = {
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GEMINI": os.getenv("GEMINI_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "XAI": os.getenv("XAI_API_KEY"),
    "OPENROUTER": os.getenv("OPENROUTER_API_KEY"),
    "QWEN": os.getenv("QWEN_API_KEY")
}

X_CRED = {
    "bearer": os.getenv("X_BEARER_TOKEN"),
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}

# استخدام الأسماء البرمجية المعتمدة لديك لتليجرام
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================
# قاعدة البيانات والفلترة
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
            id TEXT, brain TEXT, content TEXT, topic TEXT,
            impressions INTEGER, likes INTEGER, replies INTEGER,
            reposts INTEGER, engagement REAL, timestamp TEXT)""")
    conn.commit(); conn.close()

def is_clean_arabic(text):
    if not text: return False
    # منع اللغات الدخيلة والرموز غير المعتمدة
    stripped = re.sub(r'\(.*?\)', '', text)
    if re.search(r'[àâçéèêëîïôûùüÿñæœ\u3040-\u309F\u0E00-\u0E7F]', stripped): return False
    return bool(re.match(r'^[\u0600-\u06FF\s\[]', text))

# ==========================================
# 🌐 رادار الأخبار الحقيقية (Real-Time Scraper)
# ==========================================
async def fetch_real_tech_news():
    sources = ["https://www.theverge.com/ai-artificial-intelligence", 
               "https://techcrunch.com/category/artificial-intelligence/"]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(random.choice(sources))
            soup = BeautifulSoup(r.text, 'html.parser')
            articles = [a.get_text().strip() for a in soup.find_all(['h2', 'h3']) if len(a.get_text().strip())>25]
            return random.choice(articles) if articles else "تطورات AI الشخصي 2026"
    except: return "ابتكارات الذكاء الاصطناعي للأجهزة المحمولة"

# ==========================================
# 🧠 العقول الستة (Triple-Ensemble Logic)
# ==========================================
async def gemini_brain(p):
    c = genai.Client(api_key=KEYS["GEMINI"])
    res = await asyncio.to_thread(lambda: c.models.generate_content(model="gemini-2.0-flash", contents=p))
    return res.text

async def openai_brain(p):
    c = OpenAI(api_key=KEYS["OPENAI"])
    res = await asyncio.to_thread(lambda: c.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}]))
    return res.choices[0].message.content

# (بقية العقول تُضاف هنا بنفس النسق)

async def fetch_content(headline):
    topic = "الأدوات الحديثة والذكاء الاصطناعي للأفراد"
    prompt = f"أنت أيبكس، حلل هذا الخبر: ({headline}). صغ سبقاً صحفياً خليجياً فخماً يركز على فائدة الفرد."
    
    # تنفيذ الـ Triple-Ensemble (تبسيط للعرض)
    content = await gemini_brain(prompt)
    if is_clean_arabic(content):
        return content, "Gemini-2.0-Flash", topic
    return None, None, None

# ==========================================
# 💬 التفاعل الاستهدافي (Targeted Interaction)
# ==========================================
async def perform_smart_interactions(api_v2, topic):
    logger.info(f"🔍 رادار الردود يبحث عن مهتمين بـ: {topic}")
    query = f"{topic} lang:ar -is:retweet"
    try:
        search = api_v2.search_recent_tweets(query=query, max_results=INTERACTION_COUNT)
        if not search.data: return
        for tweet in search.data:
            prompt = f"رد بلهجة خليجية فخمة وذكية على: '{tweet.text}'. اربط الرد بموضوع {topic}."
            reply = await gemini_brain(prompt)
            if reply:
                api_v2.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                logger.success(f"✅ رد استهدافي ناجح")
                await asyncio.sleep(INTERACTION_GAP)
    except Exception as e: logger.error(f"Interaction error: {e}")

# ==========================================
# 📢 النشر على Telegram
# ==========================================
async def post_to_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message[:4096])
        logger.success("✅ تم الإرسال لتليجرام")
    except Exception as e: logger.error(f"Telegram failed: {e}")

# ==========================================
# 🚀 المهمة الرئيسية (The Mission)
# ==========================================
async def apex_mission():
    # إعدادات X
    api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                           access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
    
    # 1. جلب الخبر الحقيقي
    headline = await fetch_real_tech_news()
    
    # 2. توليد المحتوى
    content, brain, topic = await fetch_content(headline)
    if not content: return
    
    final_post = f"📢 [سبق صحفي]\n\n{headline}\n\n{content}"

    # 3. النشر المزدوج
    try:
        resp = api_v2.create_tweet(text=final_post[:MAX_POST_LENGTH])
        tweet_id = resp.data["id"]
        logger.success(f"🔥 نُشر على X عبر {brain}")
        await post_to_telegram(final_post)
        
        # 4. الردود الاستهدافية بعد 5 دقائق
        await asyncio.sleep(300)
        await perform_smart_interactions(api_v2, headline)
        
    except Exception as e: logger.error(f"Mission failed: {e}")

async def scheduler():
    init_db()
    while True:
        await apex_mission()
        logger.info(f"💤 استراحة محارب.. نعود بعد {POST_INTERVAL/3600} ساعات.")
        await asyncio.sleep(POST_INTERVAL)

if __name__ == "__main__":
    asyncio.run(scheduler())
