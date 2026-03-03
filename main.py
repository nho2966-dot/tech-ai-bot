import os
import asyncio
import httpx
import tweepy
import random
from loguru import logger

# --- 🔐 سحب المفاتيح من الإعدادات ---
CONFIG = {
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
auth = tweepy.OAuth1UserHandler(CONFIG["X"]["key"], CONFIG["X"]["secret"], CONFIG["X"]["token"], CONFIG["X"]["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(bearer_token=CONFIG["X"]["bearer"], consumer_key=CONFIG["X"]["key"], 
                          consumer_secret=CONFIG["X"]["secret"], access_token=CONFIG["X"]["token"], 
                          access_token_secret=CONFIG["X"]["access_s"])

# --- 🔍 محرك البحث (Tavily) لجلب أخبار حقيقية ---
async def search_tech_news():
    if not CONFIG["TAVILY"]: return "أحدث أدوات الذكاء الاصطناعي للأفراد"
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": CONFIG["TAVILY"],
        "query": "latest trending AI tools for individuals productivity 2026",
        "search_depth": "advanced",
        "max_results": 3
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload)
            results = r.json().get('results', [])
            return "\n".join([f"- {res['title']}: {res['content']}" for res in results])
    except: return "أدوات ذكاء اصطناعي لزيادة الإنتاجية"

# --- 🧠 العقول المتعددة (Gemini & Groq) ---
async def generate_content(news_context):
    sys_msg = "أنت ناصر، خبير تقني خليجي. لهجتك كويتية/سعودية بيضاء. استخدم المعلومات المقدمة لك لكتابة تغريدة رهيبة ومفيدة للأفراد. تجنب 'الثورة الصناعية الرابعة'."
    prompt = f"بناءً على هذه الأخبار:\n{news_context}\n\nاكتب تغريدة تقنية مشوقة بأسلوبك."
    
    # المحاولة مع Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={CONFIG['GEMINI']}"
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json={"contents": [{"parts": [{"text": f"{sys_msg}\n\n{prompt}"}]}]})
            if 'candidates' in r.json():
                return r.json()['candidates'][0]['content']['parts'][0]['text']
    except: pass

    # المحاولة مع Groq (البديل الصامل)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api.groq.com/openai/v1/chat/completions", 
                headers={"Authorization": f"Bearer {CONFIG['GROQ']}"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]})
            return r.json()['choices'][0]['message']['content']
    except: return None

# --- 📡 رادار الميديا (Pexels) ---
async def fetch_media():
    if not CONFIG["PEXELS"]: return None
    try:
        headers = {"Authorization": CONFIG["PEXELS"]}
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.pexels.com/videos/search?query=technology&per_page=1&orientation=portrait", headers=headers)
            v_url = r.json()['videos'][0]['video_files'][0]['link']
            v_res = await client.get(v_url)
            with open("post_media.mp4", "wb") as f: f.write(v_res.content)
            return "post_media.mp4"
    except: return None

# --- 🚀 التشغيل النهائي ---
async def main():
    logger.info("📡 جاري البحث عن أخبار طازجة...")
    news = await search_tech_news()
    
    logger.info("💡 جاري صياغة التغريدة بذكاء ناصر...")
    tweet_text = await generate_content(news)
    
    if tweet_text:
        tweet_text = tweet_text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته").strip()
        media = await fetch_media()
        try:
            if media:
                m_id = api_v1.media_upload(filename=media).media_id
                client_v2.create_tweet(text=tweet_text, media_ids=[m_id])
            else:
                client_v2.create_tweet(text=tweet_text)
            logger.success("✅ تم النشر بنجاح!")
        except Exception as e:
            logger.error(f"❌ فشل النشر: {e}")
        finally:
            if media and os.path.exists(media): os.remove(media)

if __name__ == "__main__":
    asyncio.run(main())
