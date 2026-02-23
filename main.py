import os
import re
import asyncio
import random
import tweepy
import httpx
import telegram
from datetime import datetime
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

TG_CONFIG = {
    "token": os.getenv("TG_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID")
}

# ==========================================
# 🧠 محرك العقول (نظام التبديل الذكي)
# ==========================================
async def smart_fetch_content(prompt):
    # ترتيب العقول: OpenAI أولاً ثم Groq لضمان جودة اللغة، وGemini كدعم
    brains = [
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Gemini", lambda p: genai.Client(api_key=KEYS["GEMINI"]).models.generate_content(model="gemini-2.0-flash", contents=p).text)
    ]
    
    for name, func in brains:
        try:
            if not KEYS.get(name.upper()) and name != "Gemini": continue
            logger.info(f"🔄 محاولة التوليد عبر: {name}")
            content = await asyncio.to_thread(func, prompt)
            if content and len(content) > 20: return content, name
        except Exception as e:
            logger.warning(f"⚠️ {name} فشل أو (Quota): {e}")
            continue
    return "الذكاء الاصطناعي يطور مهارات الأفراد بشكل مذهل اليوم. (تحديث سريع).", "Emergency"

# ==========================================
# 🔍 رادار Google News (الأخبار العاجلة فقط)
# ==========================================
async def fetch_fresh_news():
    # البحث عن أخبار الذكاء الاصطناعي في آخر 24 ساعة
    rss_url = "https://news.google.com/rss/search?q=AI+tools+for+individuals+when:1d&hl=ar&gl=SA&ceid=SA:ar"
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(rss_url)
            soup = BeautifulSoup(r.text, 'xml')
            items = soup.find_all('item')
            
            for item in items:
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text
                
                # التأكد أن الخبر ليس "إعلان" أو "عام جداً"
                if len(title) > 35:
                    logger.info(f"✅ تم العثور على خبر طازج: {title}")
                    return title, link
    except Exception as e:
        logger.error(f"🚨 فشل رادار الأخبار: {e}")
    
    return "تطورات جديدة في أدوات الذكاء الاصطناعي الشخصية", "https://news.google.com"

# ==========================================
# 🚀 المهمة الرئيسية (النشر البشري المحترف)
# ==========================================
async def apex_mission():
    try:
        api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                               access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
        
        # 1. جلب أحدث خبر من جوجل نيوز
        headline, source_link = await fetch_fresh_news()
        
        # 2. برومبت الصياغة البشرية (تقسيم احترافي)
        prompt = (
            f"صغ تغريدة بشرية محترفة عن هذا الخبر العاجل: ({headline}).\n\n"
            "الهيكل الصارم:\n"
            "1. ابدأ بالخبر مباشرة بلهجة خليجية بيضاء فخمة.\n"
            "2. مسافة سطر.\n"
            "3. استخدم الرمز (•) لنقاط مختصرة جداً توضح 'الفائدة للفرد'.\n"
            "4. مسافة سطر.\n"
            "5. الزبدة: (سطر واحد يختصر الموضوع).\n\n"
            "قواعد ذهبية: لا تذكر أنك بوت، لا تستخدم كلمات أعجمية غريبة، المصطلحات التقنية (الإنجليزية) بين قوسين فقط."
        )
        
        content, brain_used = await smart_fetch_content(prompt)
        
        if content:
            # 3. المنشور النهائي
            final_tweet = f"{content}\n\n🔗 المصدر الموثوق:\n{source_link}"
            
            # 4. النشر على X
            api_v2.create_tweet(text=final_tweet)
            logger.success(f"🔥 نُشر خبر (عاجل) بنجاح عبر {brain_used}")
            
            # 5. تليجرام
            if TG_CONFIG["token"]:
                try:
                    bot = telegram.Bot(token=TG_CONFIG["token"])
                    await bot.send_message(chat_id=TG_CONFIG["chat_id"], text=final_tweet)
                except: pass
    except Exception as e:
        logger.error(f"🚨 خطأ في المهمة: {e}")

# ==========================================
# ⏳ التشغيل
# ==========================================
async def main():
    logger.info("🚀 رادار أيبكس 2026 قيد التشغيل...")
    # تنفيذ المهمة فوراً عند التشغيل
    await apex_mission()

if __name__ == "__main__":
    asyncio.run(main())
