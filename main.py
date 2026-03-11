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
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

client = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🧹 LANGUAGE FILTER =================
def clean_non_ar_en(text):
    """منع الحروف الصينية، الروسية، أو أي رموز غريبة نهائياً"""
    # السماح فقط بالعربية، الإنجليزية، الأرقام، والرموز الشائعة (.,!?)
    pattern = re.compile(r'[^\u0600-\u06FF\u0750-\u077F\ufb50-\ufdff\ufe70-\ufefc\s\w.,!?;:()@#-]')
    cleaned = pattern.sub('', text)
    return cleaned

# ================= 🧠 AI ENGINE (الضبط العسكري) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.2, # تقليل جداً لمنع أي خروج عن النص أو هلوسة لغوية
                    "messages": [
                        {"role": "system", "content": system + """
- ممنوع منعاً باتاً استخدام أي حرف صيني أو روسي أو لغة غير العربية.
- لا تستخدم مقدمات مثل "في هذا المقال" أو "تعد التكنولوجيا".
- ادخل في صلب الموضوع: (المشكلة، الأداة، الحل العملي).
- اللهجة: خليجية بيضاء رصينة جداً."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            raw_text = res.json()["choices"][0]["message"]["content"].strip()
            return clean_non_ar_en(raw_text)
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("🛡️ تشغيل فحص اللغة والجودة V27...")
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    with sqlite3.connect("newsroom_v5.db") as db:
        # فحص المنشنات أولاً (الردود)
        # [دالة handle_mentions السابقة تضاف هنا بنفس الفلاتر]

        # النشر اليومي (تركيز على القيمة)
        if not db.execute("SELECT 1 FROM daily_post WHERE date=?", (today_date,)).fetchone():
            topic = "كيف تستخدم @n8n_io لربط بريدك بـ @OpenAI وتصنيف المهام آلياً؟"
            sys_msg = "أنت خبير أتمتة تقني. اشرح خطوات عملية (1, 2, 3) بدون ثرثرة."
            
            content = await ask_ai(sys_msg, f"صمم دليل عملي قصير لـ: {topic}")
            
            if content:
                # حذف أي بقايا لغوية غريبة قبل النشر
                final_post = content + "\n\n#أتمتة #تقنية #AI"
                client.create_tweet(text=final_content)
                db.execute("INSERT INTO daily_post VALUES (?)", (today_date,))
                db.commit()
                logger.success("✅ تم النشر بنجاح مع فلترة اللغة.")

if __name__ == "__main__":
    asyncio.run(main())
