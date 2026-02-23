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
# ⚙️ الربط المباشر مع الـ Secrets (حسب الصورة)
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "XAI": os.getenv("XAI_API_KEY")
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"),
    "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"),
    "ts": os.getenv("X_ACCESS_SECRET")
}

TG_CONFIG = {
    "token": os.getenv("TG_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID")
}

# ==========================================
# 🧠 محرك العقول الذكي (التبديل التلقائي)
# ==========================================
async def smart_fetch_content(prompt):
    # قائمة العقول المتاحة في الـ Secrets عندك
    brains = [
        ("Gemini", lambda p: genai.Client(api_key=KEYS["GEMINI"]).models.generate_content(model="gemini-2.0-flash", contents=p).text),
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content)
    ]
    
    for name, func in brains:
        try:
            logger.info(f"🔄 محاولة التوليد عبر عقل: {name}")
            content = await asyncio.to_thread(func, prompt)
            if content and len(content) > 10:
                return content, name
        except Exception as e:
            logger.warning(f"⚠️ {name} فشل: {e}")
            continue

    # 🛡️ بروتوكول الطوارئ (لو انقطعت كل السبل)
    return "الذكاء الاصطناعي وأدواته الحديثة هي القوة القادمة للأفراد؛ التبني المبكر يعني فرصاً لا حدود لها في الإنتاجية والإبداع. (تحديث تقني صادر عن أيبكس).", "Emergency_System"

# ==========================================
# 🚀 المهمة الرئيسية
# ==========================================
async def apex_mission():
    try:
        api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                               access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
        
        headline = "أحدث تقنيات الذكاء الاصطناعي للأفراد 2026"
        prompt = f"أنت أيبكس، خبير تقني خليجي. صغ سبقاً صحفياً فخماً عن: {headline}. ركز على الفائدة الشخصية."
        
        content, brain_used = await smart_fetch_content(prompt)
        final_post = f"📢 [أيبكس التقني]\n\n{content}\n\n#ذكاء_اصطناعي #أدوات_الذكاء_الاصطناعي"
        
        # النشر على X
        api_v2.create_tweet(text=final_post)
        logger.success(f"🔥 تم النشر بنجاح بواسطة {brain_used}")

        # إرسال تليجرام
        if TG_CONFIG["token"]:
            try:
                bot = telegram.Bot(token=TG_CONFIG["token"])
                await bot.send_message(chat_id=TG_CONFIG["chat_id"], text=final_post)
            except: logger.warning("⚠️ تليجرام لم يرسل (تحقق من ضغط Start)")

    except Exception as e:
        logger.error(f"🚨 خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(apex_mission())
