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

# ================= 🛡️ THE ULTIMATE GUARDRAIL (V36) =================
def final_validation(text):
    # 1. منع أي حرف غير العربي والإنجليزي (إزالة الروسي والصيني تماماً)
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:()@#/-]', '', text)
    # 2. منع دمج الكلمات البرمجية بكلمات عربية (مثل مركزية+center)
    forbidden_mixed = ["مركزية", "центр", "createServer", "أ.", "центраالية"]
    for word in forbidden_mixed:
        text = text.replace(word, "")
    # 3. تنظيف المسافات الزائدة الناتجة عن الحذف
    return ' '.join(text.split()).strip()

# ================= 🧠 AI ENGINE V36 (Strict Tech Editor) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.2, # تقليل الحرارة لأدنى مستوى لضمان الانضباط
                    "messages": [
                        {"role": "system", "content": system + """
- ممنوع دمج حروف عربية بإنجليزية في كلمة واحدة.
- ممنوع كتابة أكواد برمجية (Code snippets) داخل التغريدة.
- اذكر الأداة بالإنجليزية والوصف بالعربية الرصينة.
- اللهجة: خليجية بيضاء رسمية للخبراء."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            raw_text = res.json()["choices"][0]["message"]["content"]
            return final_validation(raw_text)
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("📡 تشغيل المحرر التقني V36...")
    
    # تحديد مسار تقني واضح جداً لمنع الهلوسة
    sys_msg = "أنت مهندس نظم (Systems Engineer). قدم شرحاً لخطوات ربط الأدوات بأسلوب النقاط."
    prompt = "اشرح باختصار خطوات ربط Supabase كقاعدة بيانات مع Claude لتحليل ملفات PDF."
    
    content = await ask_ai(sys_msg, prompt)
    
    if content and len(content) > 30:
        final_post = f"🏗️ مخطط العمل التقني:\n\n{content}\n\n#AI #Supabase #Claude #Architecture"
        client.create_tweet(text=final_post)
        logger.success("✅ تم النشر بنجاح وبدقة عالية!")

if __name__ == "__main__":
    asyncio.run(main())
