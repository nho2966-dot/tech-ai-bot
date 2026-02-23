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
# ⚙️ الإعدادات العامة (Apex Sovereign 2026)
# ==========================================
MAX_POST_LENGTH = 24500
DB_FILE = "apex_engine.db"
POST_INTERVAL = 21600
INTERACTION_COUNT = 5
INTERACTION_GAP = 600

KEYS = {
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GEMINI": os.getenv("GEMINI_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY")
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}

TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================
# 🛡️ الحماية والفلترة
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
            id TEXT, brain TEXT, content TEXT, topic TEXT, timestamp TEXT)""")
    conn.commit(); conn.close()

def is_clean_arabic(text):
    if not text: return False
    stripped = re.sub(r'\(.*?\)', '', text)
    if re.search(r'[àâçéèêëîïôûùüÿñæœ\u3040-\u309F\u0E00-\u0E7F]', stripped): return False
    return bool(re.match(r'^[\u0600-\u06FF\s\[]', text))

# ==========================================
# 🧠 العقول البديلة (Fault-Tolerant Brains)
# ==========================================
async def gemini_brain(p):
    client = genai.Client(api_key=KEYS["GEMINI"])
    res = await asyncio.to_thread(lambda: client.models.generate_content(model="gemini-2.0-flash", contents=p))
    return res.text

async def openai_brain(p):
    client = OpenAI(api_key=KEYS["OPENAI"])
    res = await asyncio.to_thread(lambda: client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}]))
    return res.choices[0].message.content

async def groq_brain(p):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    res = await asyncio.to_thread(lambda: client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": p}]))
    return res.choices[0].message.content

# ==========================================
# 🔄 محرك اختيار العقل الذكي (Fallback Engine)
# ==========================================
async def smart_fetch_content(prompt):
    # ترتيب العقول حسب الأفضلية
    brains = [
        ("Gemini", gemini_brain),
        ("OpenAI", openai_brain),
        ("Groq", groq_brain)
    ]
    
    for name, func in brains:
        try:
            logger.info(f"Trying brain: {name}")
            content = await func(prompt)
            if content and is_clean_arabic(content):
                return content, name
        except Exception as e:
            logger.warning(f"⚠️ {name} failed or Quota exceeded. Moving to next...")
            continue # ينتقل للعقل التالي في حال فشل الحالي
    return None, None

# ==========================================
# 🌐 رادار الأخبار الحقيقية
# ==========================================
async def fetch_real_tech_news():
    sources = ["https://www.theverge.com/ai-artificial-intelligence", 
               "https://techcrunch.com/category/artificial-intelligence/"]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(random.choice(sources))
            soup = BeautifulSoup(r.text, 'html.parser')
            articles = [a.get_text().strip() for a in soup.find_all(['h2', 'h3']) if len(a.get_text().strip())>25]
            return random.choice(articles) if articles else "مستقبل الذكاء الاصطناعي للأفراد"
    except: return "ابتكارات تقنية مذهلة في عام 2026"

# ==========================================
# 🚀 المهمة الرئيسية (The Mission)
# ==========================================
async def apex_mission():
    try:
        api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                               access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
        
        headline = await fetch_real_tech_news()
        prompt = f"أنت أيبكس، خبير تقني خليجي. حلل هذا الخبر: ({headline}). صغ سبقاً صحفياً فخماً يركز على فائدة الفرد."
        
        content, best_brain = await smart_fetch_content(prompt)
        
        if content:
            final_post = f"📢 [سبق صحفي]\n\n{headline}\n\n{content}"
            # النشر على X
            api_v2.create_tweet(text=final_post[:28000]) # دعم التغريدات الطويلة
            logger.success(f"🔥 نُشر بنجاح عبر {best_brain}")
            
            # النشر على Telegram
            if TELEGRAM_BOT_TOKEN:
                bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_post[:4096])
        else:
            logger.error("❌ فشلت جميع العقول في توليد المحتوى.")
            
    except Exception as e:
        logger.error(f"Mission Critical Error: {e}")

async def scheduler():
    init_db()
    while True:
        await apex_mission()
        await asyncio.sleep(POST_INTERVAL)

if __name__ == "__main__":
    asyncio.run(scheduler())
