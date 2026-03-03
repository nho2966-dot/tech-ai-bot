import os
import asyncio
import httpx
import tweepy
import sqlite3
from loguru import logger

# --- 🔐 الإعدادات ---
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

# --- 🧠 محرك التوليد (Groq مع Fallback Gemini) ---
async def generate_nasser_content():
    news_content = "أحدث تطبيقات الذكاء الاصطناعي للأفراد 2026"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            search = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], "query": "new AI tools productivity 2026", "max_results": 1})
            if search.status_code == 200:
                news_content = search.json().get('results', [{}])[0].get('content', news_content)
    except: logger.warning("⚠️ Tavily تأخر، نستخدم العنوان الافتراضي.")

    sys_msg = "أنت ناصر، خبير تقني خليجي. اكتب تغريدة عن أداة AI مفيدة بلهجة بيضاء. لا تذكر 'الثورة الصناعية الرابعة'."
    prompt = f"الخبر: {news_content[:500]}"

    # محاولة Groq
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]})
            data = res.json()
            if 'choices' in data: return data['choices'][0]['message']['content'].strip()
    except: pass

    # الفزعة من Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={CONF['GEMINI']}"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(url, json={"contents": [{"parts": [{"text": f"{sys_msg}\n\n{prompt}"}]}]})
            return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except: return None

# --- 📡 جلب الميديا ---
async def get_video():
    if not CONF["PEXELS"]: return None
    try:
        headers = {"Authorization": CONF["PEXELS"]}
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get("https://api.pexels.com/videos/search?query=future technology&per_page=1&orientation=portrait", headers=headers)
            v_url = r.json()['videos'][0]['video_files'][0]['link']
            res = await client.get(v_url, follow_redirects=True)
            with open("post_vid.mp4", "wb") as f: f.write(res.content)
            return "post_vid.mp4"
    except: return None

# --- 💬 نظام الردود الذكي ---
async def process_mentions():
    logger.info("💬 جاري فحص المنشن والردود...")
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return

        db = sqlite3.connect("nasser_memory.db")
        db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        
        for t in mentions[:3]: # الرد على آخر 3 منشنات
            if not db.execute("SELECT 1 FROM seen WHERE id=?", (str(t.id),)).fetchone():
                reply_text = "هلا بك! ناصر معك.. دايم بالخدمة لأي استفسار تقني يهمك. ✨"
                client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=t.id)
                db.execute("INSERT INTO seen VALUES (?)", (str(t.id),))
                db.commit()
                logger.success(f"✅ تم الرد على المنشن: {t.id}")
    except Exception as e: logger.error(f"❌ فشل الردود: {e}")

# --- 🚀 المحرك الرئيسي ---
async def run_nasser_bot():
    logger.info("🚀 تشغيل المحرك: النشر أولاً...")
    
    # 1. توليد المحتوى والميديا بالتوازي (للسرعة)
    content_task = asyncio.create_task(generate_nasser_content())
    video_task = asyncio.create_task(get_video())
    
    tweet_text = await content_task
    video_file = await video_task
    
    # 2. النشر فوراً
    if tweet_text:
        tweet_text = tweet_text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
        try:
            if video_file and os.path.exists(video_file):
                media = api_v1.media_upload(filename=video_file)
                client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                logger.success("✅ تم النشر الرئيسي مع الفيديو!")
            else:
                client_v2.create_tweet(text=tweet_text)
                logger.success("✅ تم النشر الرئيسي (نص فقط).")
        except Exception as e: logger.error(f"❌ فشل النشر على X: {e}")
        finally:
            if video_file and os.path.exists(video_file): os.remove(video_file)
    else:
        logger.critical("🚨 فشل توليد المحتوى!")

    # 3. الرد على المنشن بعد النشر
    await process_mentions()

if __name__ == "__main__":
    asyncio.run(run_nasser_bot())
