import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
from loguru import logger

# --- 🔐 سحب الإعدادات من GitHub Secrets ---
CONF = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_KEY"),
    "PEXELS": os.getenv("PEXELS_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

# إعداد X
auth = tweepy.OAuth1UserHandler(CONF["X"]["key"], CONF["X"]["secret"], CONF["X"]["token"], CONF["X"]["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(bearer_token=CONF["X"]["bearer"], consumer_key=CONF["X"]["key"], 
                          consumer_secret=CONF["X"]["secret"], access_token=CONF["X"]["token"], 
                          access_token_secret=CONF["X"]["access_s"])

# --- 🧠 المحرك الذكي (توليد مضمون 100%) ---
async def ask_ai(prompt, sys_msg):
    # المحاولة الأولى: Groq
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]})
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content'].strip()
    except: pass
    
    # المحاولة الثانية: Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={CONF['GEMINI']}"
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(url, json={"contents": [{"parts": [{"text": f"{sys_msg}\n\n{prompt}"}]}]})
            return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except: return None

# --- 💬 نظام الردود (منع الـ 403 Duplicate) ---
async def safe_reply():
    logger.info("💬 فحص المنشن للرد بذكاء...")
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id, expansions=['author_id']).data
        if not mentions: return

        db = sqlite3.connect("nasser_memory.db")
        db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        
        for t in mentions[:3]:
            if not db.execute("SELECT 1 FROM seen WHERE id=?", (str(t.id),)).fetchone():
                # توليد رد متغير لمنع التكرار
                reply_prompt = f"رد على هذا الاستفسار بلهجة كويتية/سعودية بيضاء وبشكل فريد: {t.text}"
                reply_text = await ask_ai(reply_prompt, "أنت ناصر، تقني خليجي ذكي.")
                
                # إذا فشل AI، نستخدم رد آلي بلمسة عشوائية
                if not reply_text:
                    replies = ["أبشر يا غالي، ناصر معك.. وش بغيت؟", "يا هلا.. سؤالك في المحل، ناصر بيجاوبك الحين.", "منور يا تقني! ناصر هنا للخدمة."]
                    reply_text = f"{random.choice(replies)} #{random.randint(100,999)}"

                try:
                    client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=t.id)
                    db.execute("INSERT INTO seen VALUES (?)", (str(t.id),))
                    db.commit()
                    logger.success(f"✅ تم الرد بنجاح على {t.id}")
                except: logger.warning("⚠️ تعذر الرد (مكرر أو محمي)")
    except Exception as e: logger.error(f"❌ عطل في الردود: {e}")

# --- 🚀 عملية النشر (الأولوية القصوى) ---
async def post_nasser_update():
    logger.info("🚀 تجهيز التغريدة الرئيسية...")
    
    # جلب خبر جديد
    news = "أحدث أدوات الذكاء الاصطناعي للأفراد"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            s = await client.post("https://api.tavily.com/search", json={"api_key": CONF["TAVILY"], "query": "trending AI tools 2026", "max_results": 1})
            news = s.json().get('results', [{}])[0].get('content', news)
    except: pass

    content = await ask_ai(f"اكتب تغريدة تقنية حماسية عن: {news[:500]}", "أنت ناصر، خبير تقني خليجي. لا تذكر الثورة الصناعية الرابعة.")
    
    if content:
        content = content.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
        try:
            client_v2.create_tweet(text=content)
            logger.success("✅ تم النشر الرئيسي بنجاح!")
        except Exception as e: logger.error(f"❌ فشل النشر: {e}")
    else: logger.critical("🚨 تعذر توليد محتوى!")

# --- 🎬 التشغيل بالترتيب المعتمد ---
async def main():
    # 1. انشر أولاً
    await post_nasser_update()
    # 2. رد على المتابعين
    await safe_reply()

if __name__ == "__main__":
    asyncio.run(main())
