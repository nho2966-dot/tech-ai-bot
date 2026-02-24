import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
from loguru import logger
import tweepy
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ⚙️ المفاتيح والصلاحيات
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "bearer_token": os.getenv("X_BEARER_TOKEN"),            # v2 للقراءة فقط
    "consumer_key": os.getenv("X_API_KEY"),                 # v1 للنشر
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

OFFICIAL_REFS = ["GoogleAI", "OpenAI", "DeepMind", "MetaAI", "Microsoft", "AnthropicAI", "NVIDIAAIDev"]
BLACKLIST = ["سياسة", "مخدرات", "عنصرية", "شتم", "تحريض"]

# ==========================================
# 🔑 المصادقة
# ==========================================
try:
    # v2 للقراءة
    client_v2 = tweepy.Client(
        bearer_token=X_CRED["bearer_token"],
        wait_on_rate_limit=True
    )

    # v1 للنشر
    auth_v1 = tweepy.OAuth1UserHandler(
        X_CRED["consumer_key"],
        X_CRED["consumer_secret"],
        X_CRED["access_token"],
        X_CRED["access_token_secret"]
    )
    api_v1 = tweepy.API(auth_v1)

    BOT_ID = client_v2.get_me().data.id
    logger.success("✅ المحرك انطلق، المصادقة ناجحة لكل من v1 و v2!")
except Exception as e:
    logger.error(f"❌ فشل المصادقة: {e}")
    exit()

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي
# ==========================================
async def ai_guard(prompt, mode="news"):
    if any(word in prompt.lower() for word in BLACKLIST):
        return "SKIP"

    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    
    sys_prompt = f"""أنت 'أيبكس'. خبير في الذكاء الاصطناعي وأحدث أدواته.
    - اللهجة: خليجية بيضاء (بدوية حضرية راقية).
    - القيود: يمنع ذكر 'الثورة الصناعية' نهائياً، استبدلها بـ 'الذكاء الاصطناعي وأحدث أدواته'.
    - اللغة: لا تستخدم الإنجليزية في النص، فقط بين أقواس (Name).
    - النمط: { 'اقتبس وعلق بذكاء' if mode == 'snipe' else 'صغ خبر مفيد للأفراد' }."""

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ AI: {e}")
        return "SKIP"

# ==========================================
# 🎯 القنص من المراجع الموثوقة
# ==========================================
async def snipe_official_refs():
    target = random.choice(OFFICIAL_REFS)
    logger.info(f"🎯 فحص مرجع موثوق: {target}")
    try:
        user = client_v2.get_user(username=target)
        tweets = client_v2.get_users_tweets(
            id=user.data.id,
            max_results=5,
            tweet_fields=['text', 'id']
        )

        if tweets.data:
            tweet = tweets.data[0]
            comment = await ai_guard(tweet.text, mode="snipe")
            if "SKIP" not in comment:
                await asyncio.sleep(random.randint(60, 180))
                # استخدام v1 للنشر لتجنب 401
                api_v1.update_status(status=comment, in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True)
                logger.success(f"🚀 تم قنص تغريدة من {target}!")
    except Exception as e:
        logger.error(f"❌ فشل القنص: {e}")

# ==========================================
# 📰 النشر الدوري
# ==========================================
async def post_unique_news():
    logger.info("📰 جلب أخبار الذكاء الاصطناعي وأحدث أدواته...")
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://aitnews.com/feed/", timeout=10)
            soup = BeautifulSoup(r.content, 'xml')
            item = soup.find('item')
            if item:
                link = item.link.text
                my_tweets = client_v2.get_users_tweets(id=BOT_ID, max_results=10)
                if my_tweets.data and any(link in t.text for t in my_tweets.data):
                    logger.warning("⚠️ هذا الخبر تم نشره مسبقاً، تخطي...")
                    return

                tweet_text = await ai_guard(item.title.text, mode="news")
                if "SKIP" not in tweet_text:
                    api_v1.update_status(status=f"{tweet_text}\n\n🔗 {link}")
                    logger.success("✅ تم نشر الخبر بنجاح!")
    except Exception as e:
        logger.error(f"❌ خطأ النشر: {e}")

# ==========================================
# 🚀 المحرك الرئيسي
# ==========================================
async def run_apex_engine():
    await snipe_official_refs()
    await post_unique_news()

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
