import os
import asyncio
import httpx
import tweepy
import sqlite3
from loguru import logger

# --- الإعدادات (ثابتة) ---
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

# إعداد X (v1.1 للرفع و v2 للنشر)
auth = tweepy.OAuth1UserHandler(CONF["X"]["key"], CONF["X"]["secret"], CONF["X"]["token"], CONF["X"]["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(bearer_token=CONF["X"]["bearer"], consumer_key=CONF["X"]["key"], 
                          consumer_secret=CONF["X"]["secret"], access_token=CONF["X"]["token"], 
                          access_token_secret=CONF["X"]["access_s"])

# --- نظام جلب المحتوى (Tavily + Brain) ---
async def get_fresh_content():
    try:
        # 1. البحث عن خبر طازج
        async with httpx.AsyncClient(timeout=20) as client:
            search = await client.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"], "query": "latest AI tools for individuals March 2026", "max_results": 1})
            news = search.json().get('results', [{}])[0].get('content', 'أحدث تقنيات AI')

        # 2. الصياغة عبر Groq (أو Gemini كبديل)
        sys_msg = "أنت ناصر، خبير تقني خليجي. اكتب بلهجة بيضاء تغريدة مشوقة عن الأداة التالية للأفراد."
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": news}]})
            text = res.json()['choices'][0]['message']['content']
            return text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته").strip()
    except Exception as e:
        logger.error(f"فشل توليد المحتوى: {e}")
        return None

# --- نظام الميديا (تحميل وحفظ مستقر) ---
async def download_video():
    if not CONF["PEXELS"]: return None
    try:
        headers = {"Authorization": CONF["PEXELS"]}
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.get("https://api.pexels.com/videos/search?query=ai&per_page=1&orientation=portrait", headers=headers)
            video_url = r.json()['videos'][0]['video_files'][0]['link']
            
            # تحميل الفيديو بنظام الـ Stream لتجنب التعليق
            async with client.stream("GET", video_url, follow_redirects=True) as response:
                with open("vid.mp4", "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            return "vid.mp4"
    except Exception as e:
        logger.error(f"فشل تحميل الفيديو: {e}")
        return None

# --- الردود الذكية (نظام الفلترة) ---
async def handle_mentions():
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id).data
        if not mentions: return
        
        db = sqlite3.connect("memory.db")
        db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        
        for t in mentions[:3]:
            if not db.execute("SELECT 1 FROM seen WHERE id=?", (str(t.id),)).fetchone():
                client_v2.create_tweet(text="يا هلا! ناصر معك، أبشر باللي يسرّك. التقنية بحر وحنا هنا نبسطها لك. ✨", in_reply_to_tweet_id=t.id)
                db.execute("INSERT INTO seen VALUES (?)", (str(t.id),))
        db.commit()
    except: pass

# --- التنفيذ النهائي ---
async def run_bot():
    logger.info("🚀 تشغيل المحرك الجذري...")
    
    # تنفيذ المهام بالتوازي لسرعة الإنجاز
    content_task = asyncio.create_task(get_fresh_content())
    video_task = asyncio.create_task(download_video())
    mentions_task = asyncio.create_task(handle_mentions())
    
    tweet_text, video_file, _ = await asyncio.gather(content_task, video_task, mentions_task)
    
    if tweet_text:
        try:
            if video_file and os.path.exists(video_file):
                # الرفع عبر v1.1 مع معالجة الأخطاء
                media = api_v1.media_upload(filename=video_file)
                client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                logger.success("✅ تم النشر بنجاح مع الفيديو!")
            else:
                client_v2.create_tweet(text=tweet_text)
                logger.success("✅ تم النشر (نص فقط) بسبب تعذر الفيديو.")
        except Exception as e:
            logger.error(f"❌ فشل النشر على X: {e}")
        finally:
            if video_file and os.path.exists(video_file): os.remove(video_file)
    else:
        logger.critical("🚨 لم يتم توليد أي محتوى لنشره.")

if __name__ == "__main__":
    asyncio.run(run_bot())
