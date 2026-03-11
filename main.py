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

# ================= 🧹 LANGUAGE & CLEANING =================
def clean_text(text):
    """منع الحروف الصينية والروسية والرموز الغريبة"""
    # السماح بالعربية والإنجليزية والأرقام والرموز الأساسية فقط
    pattern = re.compile(r'[^\u0600-\u06FF\u0750-\u077F\ufb50-\ufdff\ufe70-\ufefc\s\w.,!?;:()@#-]')
    cleaned = pattern.sub('', text)
    # إزالة أي مقدمات إنشائية مملة لو ظهرت
    removals = ["في هذا المقال", "تعد التكنولوجيا", "عصرنا الحالي", "時代"]
    for r in removals:
        cleaned = cleaned.replace(r, "")
    return cleaned.strip()

# ================= 🗂 DATABASE INIT =================
def init_db():
    """تجهيز الجداول لمنع الخطأ اللي ظهر لك"""
    with sqlite3.connect("newsroom_v5.db") as db:
        db.execute("CREATE TABLE IF NOT EXISTS daily_post (date TEXT PRIMARY KEY)")
        db.execute("CREATE TABLE IF NOT EXISTS seen_mentions (id TEXT PRIMARY KEY)")
        db.commit()
    logger.info("✅ تم تجهيز قاعدة البيانات بنجاح.")

# ================= 🧠 AI ENGINE =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.3, # دقة عالية لمنع الهلوسة
                    "messages": [
                        {"role": "system", "content": system + "\n- لهجة خليجية رصينة.\n- ممنوع أي حرف صيني.\n- ادخل في الحل العملي فوراً."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return clean_text(res.json()["choices"][0]["message"]["content"])
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ================= 🚀 MAIN PROCESS =================
async def main():
    init_db()
    logger.info("🛡️ فحص الجودة والنشر V28...")
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    with sqlite3.connect("newsroom_v5.db") as db:
        # فحص هل نشرنا اليوم؟
        if not db.execute("SELECT 1 FROM daily_post WHERE date=?", (today_date,)).fetchone():
            
            # اختيار موضوع "دسم" وعملي
            topics = [
                "خطوات ربط @n8n_io بـ @OpenAI لتلخيص ملفات العمل تلقائياً.",
                "كيف تفعل نظام الحماية القصوى لبياناتك الشخصية باستخدام Local LLMs.",
                "دليل عملي لاستخدام برومبتات التفكير المنطقي في Claude 4."
            ]
            
            sys_msg = "أنت مستشار تقني عملي. اشرح الطريقة بـ (الأدوات + الخطوات + الفائدة)."
            content = await ask_ai(sys_msg, random.choice(topics))
            
            if content and len(content) > 10:
                final_post = f"{content}\n\n#ذكاء_اصطناعي #تقنية #أتمتة"
                client.create_tweet(text=final_post)
                
                db.execute("INSERT INTO daily_post VALUES (?)", (today_date,))
                db.commit()
                logger.success("🔥 تم النشر بنجاح وبدون أخطاء لغوية.")
            else:
                logger.warning("⚠️ فشل توليد محتوى مناسب.")
        else:
            logger.info("📅 تم النشر مسبقاً لهذا اليوم.")

if __name__ == "__main__":
    asyncio.run(main())
