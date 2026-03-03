import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
from loguru import logger

# --- 🔐 الإعدادات ---
CONF = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

# إعداد X
client_v2 = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# --- 🧠 محرك التوليد (Groq + Gemini Fallback) ---
async def ask_brain(prompt, system_msg):
    # محاولة Groq أولاً لسرعته
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]})
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content'].strip()
    except: pass

    # محاولة Gemini إذا تعطل Groq
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={CONF['GEMINI']}"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(url, json={"contents": [{"parts": [{"text": f"{system_msg}\n\n{prompt}"}]}]})
            return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except: return None

# --- 💬 نظام الردود الذكي (يمنع التكرار 100%) ---
async def process_mentions():
    logger.info("💬 فحص المنشن للرد بذكاء فريد...")
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return

        db = sqlite3.connect("nasser_memory.db")
        db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        
        for t in mentions[:3]:
            if not db.execute("SELECT 1 FROM seen WHERE id=?", (str(t.id),)).fetchone():
                # توليد رد خاص بكل تغريدة
                sys_msg = "أنت ناصر، خبير تقني خليجي. رد بذكاء ولهجة بيضاء على المتابع. لا تكرر الردود."
                prompt = f"المتابع يسأل: {t.text}. اعطه رد قصير ومفيد."
                
                reply_text = await ask_brain(prompt, sys_msg)
                
                # إضافة لمسة عشوائية لضمان قبول X للرد
                if not reply_text:
                    reply_text = f"يا هلا بك! ناصر معك.. سؤالك ممتاز وبجاوبك عليه الحين. #{random.randint(100, 999)}"
                else:
                    reply_text = f"{reply_text} #{random.randint(100, 999)}"

                try:
                    client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=t.id)
                    db.execute("INSERT INTO seen VALUES (?)", (str(t.id),))
                    db.commit()
                    logger.success(f"✅ تم الرد الذكي على: {t.id}")
                except Exception as e:
                    logger.warning(f"⚠️ فشل إرسال الرد: {e}")
    except Exception as e:
        logger.error(f"❌ عطل في المنشن: {e}")

# --- 🚀 النشر الرئيسي ---
async def post_update():
    logger.info("🚀 تجهيز التغريدة الأساسية...")
    # بحث سريع عن خبر
    news_ctx = "أحدث أدوات الذكاء الاصطناعي المفيدة للأفراد"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            s = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": "latest AI tools individuals 2026", "max_results": 1})
            news_ctx = s.json().get('results', [{}])[0].get('content', news_ctx)
    except: pass

    content = await ask_brain(f"اكتب تغريدة تقنية حماسية عن: {news_ctx[:500]}", "أنت ناصر، تقني خليجي. تجنب ذكر الثورة الصناعية الرابعة.")
    
    if content:
        content = content.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
        try:
            client_v2.create_tweet(text=content)
            logger.success("✅ تم النشر الرئيسي!")
        except Exception as e: logger.error(f"❌ فشل النشر: {e}")

# --- 🎬 التشغيل ---
async def main():
    await post_update()   # النشر أولاً
    await process_mentions() # الرد ثانياً

if __name__ == "__main__":
    asyncio.run(main())
