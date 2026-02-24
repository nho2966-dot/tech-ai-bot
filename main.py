import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
from loguru import logger
import tweepy
import httpx
import yt_dlp
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ⚙️ الإعدادات والمفاتيح
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# حسابات للقنص (تقنية عالمية ومحلية)
SNIPE_TARGETS = ["elonmusk", "OpenAI", "sama", "AITNews", "TechWD"]

try:
    client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
    auth_v1 = tweepy.OAuth1UserHandler(X_CRED["consumer_key"], X_CRED["consumer_secret"], X_CRED["access_token"], X_CRED["access_token_secret"])
    api_v1 = tweepy.API(auth_v1)
    BOT_ID = client_v2.get_me().data.id
    logger.success("✅ المحرك جاهز للعمل يا ناصر!")
except Exception as e:
    logger.error(f"❌ خطأ اتصال: {e}"); exit()

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (أيبكس)
# ==========================================
async def ai_guard(prompt, mode="news"):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    
    prompts = {
        "news": "صغ هذا الخبر التقني بلهجة خليجية بيضاء، ركز على الفائدة للأفراد، بدون كلمات إنجليزية (إلا بين أقواس).",
        "reply": "رد بذكاء وخفة دم خليجية على هذا المنشن، خلك محفز وذكي تقنياً.",
        "snipe": "هذي تغريدة تقنية مهمة، علق عليها بذكاء (اقتباس) ووضح أثرها علينا بأسلوب خليجي ممتع."
    }

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": f"أنت 'أيبكس'. {prompts.get(mode)}"}, {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except: return "SKIP"

# ==========================================
# 🎯 محرك القنص (Sniping)
# ==========================================
async def snipe_tech_trends():
    logger.info("🎯 محاولة قنص تغريدات المشاهير...")
    target_username = random.choice(SNIPE_TARGETS)
    try:
        user = client_v2.get_user(username=target_username)
        tweets = client_v2.get_users_tweets(id=user.data.id, max_results=5, exclude=['retweets', 'replies'])
        
        if tweets.data:
            latest_tweet = tweets.data[0]
            # التأكد إنها تغريدة جديدة (آخر ساعتين)
            # ملاحظة: نحتاج tweet_fields=['created_at'] لجلب الوقت بدقة، للتسهيل سنقنص آخر واحدة
            comment = await ai_guard(latest_tweet.text, mode="snipe")
            if "SKIP" not in comment:
                # فاصل بشري قبل القنص
                await asyncio.sleep(random.randint(30, 90))
                client_v2.create_tweet(text=comment, quote_tweet_id=latest_tweet.id)
                logger.success(f"🚀 تم قنص تغريدة {target_username} بنجاح!")
    except Exception as e:
        logger.error(f"❌ خطأ قنص: {e}")

# ==========================================
# 💬 الردود والمنشن
# ==========================================
async def process_mentions():
    try:
        mentions = client_v2.get_users_mentions(id=BOT_ID, max_results=5)
        if not mentions.data: return
        for tweet in mentions.data:
            # هنا ممكن تضيف سجل (Database) بسيط لتجنب الرد مرتين، لكن للتبسيط:
            wait = random.randint(60, 150)
            await asyncio.sleep(wait)
            reply = await ai_guard(tweet.text, mode="reply")
            if "SKIP" not in reply:
                client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                logger.success(f"✅ تم الرد على {tweet.id}")
    except Exception as e: logger.error(f"❌ خطأ منشن: {e}")

# ==========================================
# 🚀 تشغيل المحرك الكامل
# ==========================================
async def run_apex_engine():
    # 1. القنص (مرة واحدة في الدورة)
    await snipe_tech_trends()
    
    # 2. الردود
    await process_mentions()
    
    # 3. النشر الدوري (الخبر)
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://aitnews.com/feed/", timeout=10)
            soup = BeautifulSoup(r.content, 'xml')
            item = soup.find('item')
            if item:
                txt = await ai_guard(item.title.text, mode="news")
                if "SKIP" not in txt:
                    client_v2.create_tweet(text=f"{txt}\n\n🔗 {item.link.text}")
                    logger.success("✅ تم نشر الخبر الدوري!")
    except Exception as e: logger.error(f"❌ خطأ نشر: {e}")

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
