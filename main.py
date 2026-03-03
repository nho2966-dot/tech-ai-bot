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
    "PEXELS": os.getenv("PEXELS_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

# إعداد مكتبات X
auth = tweepy.OAuth1UserHandler(CONF["X"]["key"], CONF["X"]["secret"], CONF["X"]["token"], CONF["X"]["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(bearer_token=CONF["X"]["bearer"], consumer_key=CONF["X"]["key"], 
                          consumer_secret=CONF["X"]["secret"], access_token=CONF["X"]["token"], 
                          access_token_secret=CONF["X"]["access_s"])

# --- 🗄️ الذاكرة لمنع التكرار ---
db = sqlite3.connect("nasser_memory.db")
sql = db.cursor()
sql.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY)")
db.commit()

# --- 🛡️ فلتر ناصر ---
def clean_nasser(text):
    if not text: return ""
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    return text.strip()

# --- 🧠 العقول المتعددة (التبديل الآلي) ---
async def ask_brain(prompt, system_msg):
    # الخيار الأول: Groq (سريع جداً)
    if CONF["GROQ"]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]})
                return clean_nasser(r.json()['choices'][0]['message']['content'])
        except: logger.warning("⚠️ Groq تعثر، ننتقل لـ Gemini...")

    # الخيار الثاني: Gemini
    if CONF["GEMINI"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={CONF['GEMINI']}"
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(url, json={"contents": [{"parts": [{"text": f"{system_msg}\n\n{prompt}"}]}]})
                return clean_nasser(r.json()['candidates'][0]['content']['parts'][0]['text'])
        except: pass
    return None

# --- 🔍 رادار البحث عن أخبار ---
async def get_latest_news():
    if not CONF["TAVILY"]: return "أدوات ذكاء اصطناعي مفيدة للأفراد 2026"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], "query": "new AI tools for individuals productivity March 2026",
                "max_results": 2})
            return "\n".join([res['content'] for res in r.json().get('results', [])])
    except: return "أحدث تقنيات الذكاء الاصطناعي للأفراد"

# --- 📡 رادار الميديا ---
async def fetch_video():
    if not CONF["PEXELS"]: return None
    try:
        headers = {"Authorization": CONF["PEXELS"]}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get("https://api.pexels.com/videos/search?query=tech&per_page=5&orientation=portrait", headers=headers)
            video_url = random.choice(r.json()['videos'])['video_files'][0]['link']
            res = await client.get(video_url, follow_redirects=True)
            with open("temp_vid.mp4", "wb") as f: f.write(res.content)
            return "temp_vid.mp4"
    except: return None

# --- 🐦 وظيفة الردود الذكية ---
async def handle_mentions():
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return
        
        for tweet in mentions[:3]:
            sql.execute("SELECT 1 FROM processed WHERE id=?", (str(tweet.id),))
            if not sql.fetchone():
                reply = await ask_brain(f"رد بذكاء ولهجة خليجية على: {tweet.text}", "أنت ناصر، خبير تقني خليجي لبق.")
                if reply:
                    client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    sql.execute("INSERT INTO processed VALUES (?)", (str(tweet.id),))
                    db.commit()
                    logger.success(f"✅ تم الرد على {tweet.id}")
    except Exception as e: logger.error(f"❌ خطأ الردود: {e}")

# --- 🚀 النشر الرئيسي ---
async def post_now():
    logger.info("📡 جاري تحضير المحتوى...")
    news_ctx = await get_latest_news()
    content = await ask_brain(f"بناءً على هذا الخبر: {news_ctx}, اكتب تغريدة خليجية حماسية للأفراد.", "أنت ناصر، خبير تقني خليجي.")
    
    if content:
        video = await fetch_video()
        try:
            if video:
                m_id = api_v1.media_upload(filename=video).media_id
                client_v2.create_tweet(text=content, media_ids=[m_id])
            else:
                client_v2.create_tweet(text=content)
            logger.success("✅ تم النشر بنجاح!")
        except Exception as e: logger.error(f"❌ خطأ النشر: {e}")
        finally:
            if video and os.path.exists(video): os.remove(video)

# --- 🎬 التشغيل ---
async def main():
    # 1. رد على الناس
    await handle_mentions()
    # 2. انشر تغريدة جديدة
    await post_now()

if __name__ == "__main__":
    asyncio.run(main())
