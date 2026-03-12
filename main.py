import os
import asyncio
import httpx
import tweepy
import sqlite3
import re
import random
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

client = tweepy.Client(
    consumer_key=CONF["X"]["key"], consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"], access_token_secret=CONF["X"]["access_s"]
)

# ================= 🛡️ THE ELITE FILTER V35 =================
def elite_polish(text):
    # إزالة أي حروف غير العربية والإنجليزية والرموز التقنية
    text = re.sub(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', '', text)
    # تنظيف الكلمات المهجنة أو "الهبد" اللغوي
    bad_phrases = ["هاو،", "بيتكون لدينا", "بناءً على حاجاتك", "إلهام وتصميم"]
    for phrase in bad_phrases:
        text = text.replace(phrase, "")
    return text.strip()

# ================= 🧠 AI ENGINE V35 (Visual & Interactive) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.6, 
                    "messages": [
                        {"role": "system", "content": system + """
- اللهجة: خليجية تقنية متمكنة (White Dialect).
- الهيكل: (المشكلة -> المخطط التقني -> الأداة -> النتيجة).
- لا تستخدم لغة عاطفية، استخدم لغة هندسية (Engineering Language).
- اذكر بوضوح كيف تتدفق البيانات بين الأدوات (Workflow)."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return elite_polish(res.json()["choices"][0]["message"]["content"])
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("📡 تشغيل محرك النخبة V35...")
    
    # جلب سياق تقني عن بناء أنظمة AI شخصية
    context = "How to build a personal RAG system using Supabase and LangChain 2026"
    
    sys_msg = "أنت Solution Architect. قدم للناس Blueprint حقيقي لبناء نظامهم الخاص."
    
    prompt = f"بناءً على {context}، صمم تغريدة تشرح الـ Workflow التقني لربط بيانات المستخدم بـ Supabase كمتجهات واسترجاعها بـ Claude."
    
    content = await ask_ai(sys_msg, prompt)
    
    if content:
        # إضافة وصف المخطط البصري لتعزيز الفهم
        diagram_desc = ""
        
        final_post = f"🏗️ مخطط هندسي (System Blueprint):\n\n{content}\n\n{diagram_desc}\n\n#Supabase #LangChain #RAG #Architecture"
        
        # نشر التغريدة
        client.create_tweet(text=final_post)
        logger.success("✅ تم نشر المخطط الهندسي بنجاح!")

if __name__ == "__main__":
    asyncio.run(main())
