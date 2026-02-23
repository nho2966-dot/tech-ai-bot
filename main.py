import os
import re
import asyncio
import random
import tweepy
import httpx
from loguru import logger
from google import genai
from openai import OpenAI
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ الربط والسيادة (Secrets)
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

# ==========================================
# 🧠 نظام العقول المتعاقبة (The Succession Brains)
# ==========================================
async def smart_fetch_content(prompt):
    # قائمة العقول المتاحة بترتيب الأولوية
    brains = [
        ("Gemini", lambda p: genai.Client(api_key=KEYS["GEMINI"]).models.generate_content(model="gemini-2.0-flash", contents=p).text),
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content)
    ]
    
    for name, func in brains:
        try:
            # التأكد من وجود المفتاح قبل المحاولة
            if not KEYS.get(name.upper()):
                continue
                
            content = await asyncio.to_thread(func, prompt)
            if content and len(content) > 40:
                logger.info(f"💡 تمت الصياغة بواسطة عقل: {name}")
                return content.strip()
        except Exception as e:
            logger.warning(f"⚠️ العقل {name} اعتذر عن العمل: {e}")
            continue
    return None

# ==========================================
# 🔍 رادار الذكاء الاصطناعي (أخبار الأفراد)
# ==========================================
async def get_latest_insider_news():
    queries = [
        "أحدث أدوات الذكاء الاصطناعي للأفراد 2026",
        "new AI tools hidden features 2026",
        "ChatGPT vs Claude vs Gemini 2026 comparison"
    ]
    query = random.choice(queries)
    rss_url = f"https://news.google.com/rss/search?q={query}+when:24h&hl=ar&gl=SA&ceid=SA:ar"
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(rss_url)
            soup = BeautifulSoup(r.text, 'xml')
            items = soup.find_all('item')
            if items:
                # اختيار خبر عشوائي لضمان التجديد (Freshness)
                item = random.choice(items[:5]) 
                return item.title.text, item.link.text
    except Exception as e:
        logger.error(f"News Fetch Error: {e}")
    return None, None

# ==========================================
# 🚀 المهمة الرئيسية (Apex Execution)
# ==========================================
async def run_apex_bot():
    logger.info("⚙️ انطلاق منظومة أيبكس بالعقول المتعاقبة...")
    
    client_v2 = tweepy.Client(
        consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
        access_token=X_CRED["at"], access_token_secret=X_CRED["ts"],
        wait_on_rate_limit=True
    )

    # جلب الخبر
    headline, source_link = await get_latest_insider_news()
    
    if headline:
        prompt = (
            f"بصفتك خبير تقني خليجي، حلل هذا الخبر: ({headline}).\n"
            "اكتب تغريدة دسمة للأفراد مقسمة كالتالي:\n"
            "🔹 الخبر بعمق: (شرح التحديث).\n"
            "✨ الخفايا: (ميزة خفية أو مقارنة).\n"
            "🛠 الجانب التطبيقي: (كيف يستفيد المتابع الآن؟).\n"
            "📍 الزبدة: (سطر الختام).\n\n"
            "قواعد: أسلوب بشري، مصطلحات إنجليزية (بين أقواس)، لا تذكر أنك بوت."
        )
        
        final_content = await smart_fetch_content(prompt)
        
        if final_content:
            try:
                tweet_text = f"{final_content}\n\n🔗 تفاصيل الخبر:\n{source_link}"
                client_v2.create_tweet(text=tweet_text)
                logger.success("✅ تم النشر بنجاح!")
            except Exception as e:
                logger.error(f"❌ خطأ في النشر: {e}")
    else:
        logger.warning("📭 لم يتم العثور على أخبار جديدة في هذه الدورة.")

if __name__ == "__main__":
    asyncio.run(run_apex_bot())
