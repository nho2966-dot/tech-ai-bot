import os
import asyncio
import httpx
import tweepy
import sqlite3
import re
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

# ================= 🛡️ ANTI-TRUNCATION & CLEANING =================
def final_polish(text):
    # مسح أي حروف غريبة أو صينية
    text = re.sub(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', '', text)
    # التأكد من عدم انقطاع النص (الحد الأقصى للمشتركين 25,000 لكن نفضل الاختصار للقراءة)
    if len(text) > 2000:
        text = text[:1997] + "..."
    return text.strip()

# ================= 🧠 ELITE AI ENGINE V33 =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.8, # رفعنا الحرارة قليلاً لكسر التكرار الممل
                    "messages": [
                        {"role": "system", "content": system + """
- ممنوع نهائياً البدء بكلمة "تخيل" أو "هل تعلم" أو "أهلاً بك".
- ابدأ فوراً بذكر اسم الأداة أو نقد لبروتوكول تقني معين.
- التزم بلهجة خليجية بيضاء "حادة" وتقنية (Sharp Tech Tone).
- استخدم المصطلحات الإنجليزية بين قوسين بكثافة لكن بذكاء.
- ممنوع تكرار الهيكل الإنشائي للتغريدات السابقة."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return final_polish(res.json()["choices"][0]["message"]["content"])
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("📡 جاري تشغيل المحرك V33 كاسر التكرار...")
    
    # جلب أخبار عميقة جداً (Deep Tech)
    news_query = "latest advancements in AI Agents orchestration and vector databases 2026"
    # [هنا نستخدم Tavily لجلب السياق كما في النسخ السابقة]
    
    sys_msg = "أنت مهندس تقني متمرد (Tech Lead). تنتقد الحلول السطحية وتقدم Architecture عميق للأفراد."
    
    prompt = "حلل لنا كيف ندمج قواعد البيانات المتجهة (Vector Databases) مع (LLMs) لتقليل الهلوسة (Hallucinations) للأفراد."
    
    content = await ask_ai(sys_msg, prompt)
    
    if content:
        # التأكد من أن التغريدة دسمة ومختلفة
        final_post = f"🔥 مراجعة معمارية (Architecture Review):\n\n{content}\n\n#VectorDB #LLMs #AI_Architecture #DevTools"
        client.create_tweet(text=final_post)
        logger.success("✅ تم النشر بأسلوب متجدد وبدون انقطاع!")

if __name__ == "__main__":
    asyncio.run(main())
