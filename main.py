import os
import asyncio
import httpx
import tweepy
import sqlite3
import re
import random
from datetime import datetime, timezone
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"), # تحتاج مفتاح من tavily.com للأخبار الطازجة
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

client = tweepy.Client(
    consumer_key=CONF["X"]["key"], consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"], access_token_secret=CONF["X"]["access_s"]
)

# ================= 🛡️ THE IRON FILTER (V30) =================
def extreme_clean(text):
    # مسح الصيني والرموز الغريبة والكلمات الإنشائية
    text = re.sub(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', '', text)
    forbidden = ["节点", "時代", "أهلاً بك", "في هذا المقال", "نود أن نوضح"]
    for word in forbidden:
        text = text.replace(word, "")
    return text.strip()

# ================= 🔍 NEWS ENGINE (أخبار طازجة) =================
async def get_fresh_news():
    """البحث عن آخر أخبار AI للأفراد في آخر 24 ساعة"""
    try:
        async with httpx.AsyncClient() as c:
            # نبحث عن أخبار أدوات مثل OpenAI, Anthropic, Google, n8n
            query = "latest AI tools news for individuals March 2026"
            res = await c.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"],
                "query": query,
                "search_depth": "advanced",
                "days": 1
            })
            results = res.json().get('results', [])
            return "\n".join([f"- {r['title']}: {r['content'][:200]}" for r in results[:3]])
    except: return "لا توجد أخبار عاجلة حالياً، سأعتمد على المعلومات التحليلية."

# ================= 🧠 AI ENGINE =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": system + "\n- لهجة خليجية رصينة.\n- ادخل في الخبر أو الحل فوراً."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return extreme_clean(res.json()["choices"][0]["message"]["content"])
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("📡 جاري جلب الأخبار الطازجة وتوليد المحتوى...")
    
    # 1. جلب الخبر
    news_context = await get_fresh_news()
    
    # 2. صياغة المحتوى بناءً على الخبر
    sys_msg = """أنت محرر تقني استقصائي (Journalistic Scoop). 
    مهمتك: صياغة خبر طازج أو أداة جديدة ظهرت اليوم. 
    الهيكل: [الخبر] ثم [كيف تستفيد منه كفرد] ثم [خطوة عملية]."""
    
    prompt = f"هذه سياقات للأخبار الحالية:\n{news_context}\n\nاصنع تغريدة احترافية دسمة بناءً على أهم خبر فيها."
    
    content = await ask_ai(sys_msg, prompt)
    
    if content:
        # إضافة هاشتاقات ذكية وإشارات
        final_post = f"🚨 جديد اليوم:\n\n{content}\n\n#ذكاء_اصطناعي #أخبار_التقنية #AI_News"
        client.create_tweet(text=final_post)
        logger.success("🔥 تم نشر الخبر الطازج بنجاح!")

if __name__ == "__main__":
    asyncio.run(main())
