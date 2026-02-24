import os
import asyncio
import random
from datetime import datetime, timezone
from loguru import logger
import tweepy
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ⚙️ الإعدادات والمفاتيح
# ==========================================
X_CRED = {
    "bearer_token": os.getenv("X_BEARER_TOKEN"),
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

OFFICIAL_REFS = ["GoogleAI", "OpenAI", "DeepMind", "MetaAI", "Microsoft", "AnthropicAI", "NVIDIAAIDev"]
BLACKLIST = ["سياسة", "مخدرات", "عنصرية", "شتم", "تحريض", "مظاهرات"]
RSS_FEEDS = ["https://aitnews.com/feed/", "https://www.tech-wd.com/wd/feed/"]

try:
    client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
    auth_v1 = tweepy.OAuth1UserHandler(X_CRED["consumer_key"], X_CRED["consumer_secret"], X_CRED["access_token"], X_CRED["access_token_secret"])
    api_v1 = tweepy.API(auth_v1)
    BOT_ID = client_v2.get_me().data.id
    logger.success("✅ المحرك انطلق يا ناصر.. الذاكرة والترند والقنص جاهزة!")
except Exception as e:
    logger.error(f"❌ فشل الاتصال: {e}"); exit()

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (أيبكس الخليجي)
# ==========================================
async def ai_guard(prompt, mode="news", trend_topic=None):
    if any(word in prompt.lower() for word in BLACKLIST): return "SKIP"

    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
    
    trend_insert = f" (حاول تدمج موضوع '{trend_topic}' بشكل طبيعي إذا كان مناسب)" if trend_topic else ""
    
    sys_prompt = f"""أنت 'أيبكس'. خبير في الذكاء الاصطناعي وأحدث أدواته.
    - اللهجة: خليجية بيضاء راقية.
    - المصطلحات: استبدل 'الثورة الصناعية' بـ 'الذكاء الاصطناعي وأحدث أدواته'.
    - اللغة: لا تستخدم الإنجليزية إلا بين أقواس (Name).
    - النمط: {mode}. {trend_insert}."""

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except: return "SKIP"

# ==========================================
# 📈 محرك تحليل الترند (Trending)
# ==========================================
async def get_saudi_trend():
    try:
        # جلب الترندات (نستخدم API v1.1 لجلب الترندات الجغرافية)
        # WOEID للسعودية هو 23424938
        trends = api_v1.get_place_trends(id=23424938)
        top_trend = trends[0]['trends'][0]['name']
        logger.info(f"📊 الترند الحالي في السعودية: {top_trend}")
        return top_trend
    except:
        return None

# ==========================================
# 🎯 محرك القنص المحدث
# ==========================================
async def snipe_official_refs(trend=None):
    target = random.choice(OFFICIAL_REFS)
    try:
        user = client_v2.get_user(username=target)
        tweets = client_v2.get_users_tweets(id=user.data.id, max_results=5)
        if tweets.data:
            tweet = tweets.data[0]
            comment = await ai_guard(tweet.text, mode="snipe", trend_topic=trend)
            if "SKIP" not in comment:
                await asyncio.sleep(random.randint(120, 300))
                client_v2.create_tweet(text=comment, quote_tweet_id=tweet.id)
                logger.success(f"🚀 تم قنص تغريدة من {target}")
    except Exception as e: logger.error(f"❌ خطأ قنص: {e}")

# ==========================================
# 📰 محرك النشر الفريد (منع التكرار)
# ==========================================
async def post_unique_news(trend=None):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(random.choice(RSS_FEEDS), timeout=10)
            soup = BeautifulSoup(r.content, 'xml')
            items = soup.find_all('item')
            
            my_tweets = client_v2.get_users_tweets(id=BOT_ID, max_results=15)
            posted_urls = [t.text for t in my_tweets.data] if my_tweets.data else []

            for item in items:
                link = item.link.text
                if any(link in t for t in posted_urls): continue
                
                txt = await ai_guard(item.title.text, mode="news", trend_topic=trend)
                if "SKIP" not in txt:
                    client_v2.create_tweet(text=f"{txt}\n\n🔗 {link}")
                    logger.success(f"✅ خبر جديد: {item.title.text}")
                    return True
        return False
    except Exception as e: logger.error(f"❌ خطأ نشر: {e}"); return False

# ==========================================
# 🚀 المحرك الرئيسي (Apex Engine)
# ==========================================
async def run_apex_engine():
    # 1. تحليل الترند أولاً
    current_trend = await get_saudi_trend()
    
    # 2. القنص (3 محاولات بفاصل بشري)
    for _ in range(3):
        await snipe_official_refs(trend=current_trend)
        await asyncio.sleep(random.randint(600, 900))

    # 3. النشر الدوري للأخبار (3 أخبار فريدة)
    published = 0
    for _ in range(10): # 10 محاولات كحد أقصى لإيجاد 3 أخبار جديدة
        if published >= 3: break
        if await post_unique_news(trend=current_trend):
            published += 1
            await asyncio.sleep(random.randint(900, 1200)) # فاصل 15-20 دقيقة

async def scheduler():
    while True:
        logger.info("🔄 تبدأ دورة العمل الآن...")
        await run_apex_engine()
        logger.info("⏰ دورة كاملة انتهت. انتظار ساعة...")
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(scheduler())
