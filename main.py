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

# ================= 🛡️ THE PRO FILTER (V34) =================
def pro_clean(text):
    text = re.sub(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', '', text) # حذف الصيني
    # حذف الافتتاحيات المملة والكلمات الأكاديمية الزائدة
    boring_stuff = ["نقدم لكم", "تخيل", "مما يسمح بـ", "عزيزي المتابع"]
    for word in boring_stuff:
        text = text.replace(word, "")
    return text.strip()

# ================= 🧠 AI ENGINE V34 (Practical Expert) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.85, # رفعنا الحرارة لكسر الجمود
                    "messages": [
                        {"role": "system", "content": system + """
- اللهجة: خليجية بيضاء "حريفة" (Tech Savvy).
- القاعدة الذهبية: (مشكلة تقنية -> أداة محددة -> كود أو برومبت أو طريقة ربط).
- ممنوع الشرح النظري البحت. نبي "تطبيق عملي" للأفراد.
- اذكر اسم أداة مشهورة (مثل @pinecone, @LangChainAI, @supabase) وأشر لها."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return pro_clean(res.json()["choices"][0]["message"]["content"])
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("📡 جاري توليد محتوى 'تطبيقي' دسم V34...")
    
    # جلب سياق من Tavily لضمان الحداثة
    news_context = "Best no-code tools to build RAG systems for personal use 2026"
    
    sys_msg = "أنت مهندس (RAG Architect) ممارس. لا تنظر، بل أعطِ خطوات التنفيذ للأفراد."
    
    prompt = f"بناءً على هذا السياق: {news_context}\nصمم تغريدة تشرح كيف يبني الشخص 'ذاكرة ثانية' لنفسه باستخدام Vector DB بدون تعقيد برمي."
    
    content = await ask_ai(sys_msg, prompt)
    
    if content:
        final_post = f"🛠️ من الميدان التقني (Practical AI):\n\n{content}\n\n#RAG #Pinecone #LLMs #أتمتة"
        client.create_tweet(text=final_post)
        logger.success("✅ تم النشر بأسلوب تطبيقي وعملي!")

if __name__ == "__main__":
    asyncio.run(main())
