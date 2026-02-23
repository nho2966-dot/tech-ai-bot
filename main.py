import os
import re
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
# ⚙️ الإعدادات والربط مع Secrets
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY")
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}

TG_CONFIG = {
    "token": os.getenv("TG_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID")
}

# المصادر الموثوقة (عالمية، عربية، خليجية)
TRUSTED_SOURCES = {
    "Global": [
        "https://www.theverge.com/ai-artificial-intelligence",
        "https://techcrunch.com/category/artificial-intelligence/",
        "https://www.wired.com/tag/artificial-intelligence/"
    ],
    "Regional": [
        "https://aitnews.com",  # البوابة العربية للأخبار التقنية
        "https://www.skynewsarabia.com/technology"
    ]
}

# ==========================================
# 🧠 محرك العقول (نظام المناوبة ضد الانهيار)
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
    brains = [("Gemini", gemini_brain), ("OpenAI", openai_brain), ("Groq", groq_brain)]
    for name, func in brains:
        if not KEYS.get(name.upper()) and name != "Gemini": continue
        try:
            logger.info(f"🔄 محاولة التوليد عبر: {name}")
            content = await func(prompt)
            if content and len(content) > 10: return content, name
        except Exception as e:
            logger.warning(f"⚠️ {name} واجه مشكلة: {e}")
            continue
    return "الذكاء الاصطناعي يغير قواعد اللعبة للأفراد؛ الأدوات الجديدة هي استثمارك الحقيقي في 2026.", "Manual_Safety"

# ==========================================
# 🔍 رادار الأخبار الموثوقة (Anti-Hallucination)
# ==========================================
async def fetch_verified_news():
    cat = random.choice(list(TRUSTED_SOURCES.keys()))
    source = random.choice(TRUSTED_SOURCES[cat])
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            r = await client.get(source, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.text, 'html.parser')
            articles = []
            for link in soup.find_all('a', href=True):
                title = link.get_text().strip()
                if len(title) > 45 and any(kw in title.lower() for kw in ['ai', 'ذكاء', 'tech', 'apple', 'google', 'تطبيق']):
                    url = link['href']
                    if not url.startswith('http'):
                        url = ("https://aitnews.com" if "aitnews" in source else "https://www.theverge.com") + url
                    articles.append((title, url))
            if articles: return random.choice(articles)
    except: pass
    return "إطلاق أدوات ذكاء اصطناعي جديدة لتعزيز الإنتاجية الشخصية", "https://news.google.com"

# ==========================================
# 🚀 المهمة السيادية (The Mission)
# ==========================================
async def apex_mission():
    try:
        api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                               access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
        
        # 1. جلب خبر حقيقي وموثوق
        headline, source_url = await fetch_verified_news()
        
        # 2. برومبت الهندسة البشرية (تقسيم احترافي + لهجة خليجية)
        prompt = (
            f"حلل هذا الخبر الحقيقي: ({headline}).\n\n"
            "المطلوب صياغة تغريدة احترافية بالهيكل التالي:\n"
            "1. السطر الأول: الخبر بلهجة خليجية بيضاء (فخمة ومباشرة).\n"
            "2. مسافة سطر.\n"
            "3. قائمة نقاط (Bullets) تشرح فائدة الخبر للفرد وكيف يستخدمه.\n"
            "4. مسافة سطر.\n"
            "5. 'الخلاصة' في سطر واحد فقط.\n\n"
            "شروط صارمة: أسلوب بشري 100%، لا تذكر أنك بوت، المصطلحات التقنية بين قوسين بالإنجليزية، ممنوع الهلوسة."
        )
        
        content, brain_used = await smart_fetch_content(prompt)
        
        if content:
            # 3. دمج المحتوى مع المصدر
            final_tweet = f"{content}\n\n🔗 المصدر الموثوق:\n{source_url}"
            
            # 4. النشر على X
            api_v2.create_tweet(text=final_tweet)
            logger.success(f"🔥 نُشر بنجاح عبر {brain_used}")
            
            # 5. تليجرام (اختياري)
            if TG_CONFIG["token"]:
                try:
                    bot = telegram.Bot(token=TG_CONFIG["token"])
                    await bot.send_message(chat_id=TG_CONFIG["chat_id"], text=final_tweet)
                except: pass
    except Exception as e:
        logger.error(f"🚨 خطأ حرج: {e}")

# ==========================================
# ⏳ المجدول الزمني
# ==========================================
async def main():
    logger.info("🚀 تشغيل نظام أيبكس المطور 2026")
    while True:
        await apex_mission()
        # النشر كل 6 ساعات (21600 ثانية)
        await asyncio.sleep(21600)

if __name__ == "__main__":
    asyncio.run(main())
