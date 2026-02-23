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
POST_INTERVAL = 21600  # كل 6 ساعات
INTERACTION_COUNT = 5   # عدد الردود الاستهدافية
INTERACTION_GAP = 600   # 10 دقائق بين كل رد

# جلب المفاتيح من البيئة (Secrets)
KEYS = {
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GEMINI": os.getenv("GEMINI_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY")
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"), 
    "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), 
    "ts": os.getenv("X_ACCESS_SECRET")
}

TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================
# 🛡️ قاعدة البيانات والفلترة
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
            id TEXT, brain TEXT, content TEXT, topic TEXT, timestamp TEXT)""")
    conn.commit(); conn.close()

def is_clean_arabic(text):
    if not text: return False
    # إزالة النصوص بين الأقواس لفحص جودة العربي
    stripped = re.sub(r'\(.*?\)', '', text)
    if re.search(r'[àâçéèêëîïôûùüÿñæœ\u3040-\u309F\u0E00-\u0E7F]', stripped): return False
    return bool(re.match(r'^[\u0600-\u06FF\s\[]', text))

# ==========================================
# 🧠 العقول والتبديل التلقائي (Fallback System)
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

async def smart_fetch_content(prompt):
    brains = [
        ("Gemini", gemini_brain),
        ("OpenAI", openai_brain),
        ("Groq", groq_brain)
    ]
    for name, func in brains:
        if not KEYS.get(name.upper()) and name != "Gemini": continue 
        try:
            logger.info(f"🔄 محاولة التوليد عبر: {name}")
            content = await func(prompt)
            if content and is_clean_arabic(content):
                return content, name
        except Exception as e:
            logger.warning(f"⚠️ {name} واجه مشكلة (Quota/Error). ننتقل للمحرك التالي...")
            continue
    return None, None

# ==========================================
# 🌐 رادار الأخبار الحقيقية (Scraper)
# ==========================================
async def fetch_real_tech_news():
    sources = ["https://www.theverge.com/ai-artificial-intelligence", 
               "https://techcrunch.com/category/artificial-intelligence/"]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(random.choice(sources))
            soup = BeautifulSoup(r.text, 'html.parser')
            articles = [a.get_text().strip() for a in soup.find_all(['h2', 'h3']) if len(a.get_text().strip())>25]
            return random.choice(articles) if articles else "الذكاء الاصطناعي للأفراد في 2026"
    except: return "أحدث أدوات الذكاء الاصطناعي والتقنيات الشخصية"

# ==========================================
# 🚀 المهمة السيادية (النشر والتفاعل)
# ==========================================
async def apex_mission():
    try:
        # إعداد عملاء تويتر
        api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                               access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
        
        # 1. جلب خبر حقيقي
        headline = await fetch_real_tech_news()
        
        # 2. توليد محتوى خليجي فخم
        prompt = f"أنت أيبكس، خبير تقني خليجي ذكي. حلل الخبر التالي: ({headline}). صغ سبقاً صحفياً فخماً يركز على فائدة الفرد واستخدام أدوات الذكاء الاصطناعي لزيادة الإنتاجية."
        content, best_brain = await smart_fetch_content(prompt)
        
        if content:
            final_post = f"📢 [سبق صحفي]\n\n{headline}\n\n{content}"
            
            # 3. النشر على X
            api_v2.create_tweet(text=final_post[:28000])
            logger.success(f"🔥 نُشرت التغريدة بنجاح عبر محرك {best_brain}")
            
            # 4. النشر على Telegram (بشكل آمن لا يوقف الكود)
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=final_post[:4096])
                    logger.success("✅ تم إرسال النسخة لتليجرام")
                except Exception as tg_e:
                    logger.warning(f"⚠️ فشل إرسال تليجرام (تأكد من ضغط Start): {tg_e}")
            
            # 5. الردود الاستهدافية (تبدأ بعد 5 دقائق من النشر)
            await asyncio.sleep(300)
            await perform_smart_interactions(api_v2, headline)
            
        else:
            logger.error("❌ تعذرت جميع العقول عن توليد المحتوى.")
            
    except Exception as e:
        logger.error(f"🚨 خطأ حرج في المهمة: {e}")

async def perform_smart_interactions(api_v2, topic):
    logger.info(f"🔍 البحث عن مهتمين بموضوع: {topic}")
    query = f"{topic} lang:ar -is:retweet"
    try:
        search = api_v2.search_recent_tweets(query=query, max_results=INTERACTION_COUNT)
        if not search.data: return
        for tweet in search.data:
            # استخدام Groq للردود لأنه سريع جداً ومجاني حالياً
            reply_prompt = f"رد بلهجة خليجية ذكية وفخمة على: '{tweet.text}'. اربط الرد بـ {topic}."
            reply_text, _ = await smart_fetch_content(reply_prompt)
            if reply_text:
                api_v2.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                logger.success(f"✅ تم الرد استهدفياً")
                await asyncio.sleep(INTERACTION_GAP)
    except Exception as e: logger.error(f"Interaction error: {e}")

# ==========================================
# ⏳ المجدول الزمني
# ==========================================
async def scheduler():
    init_db()
    logger.info("🚀 تشغيل أيبكس - نسخة السيادة 2026")
    while True:
        await apex_mission()
        logger.info(f"💤 نوبة استراحة. النشر القادم بعد {POST_INTERVAL/3600} ساعات.")
        await asyncio.sleep(POST_INTERVAL)

if __name__ == "__main__":
    asyncio.run(scheduler())
