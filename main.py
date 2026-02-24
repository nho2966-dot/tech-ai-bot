import os
import asyncio
import random
import time
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

# ==========================================
# إعداد Tweepy (الاتصال الآمن)
# ==========================================
try:
    client_v2 = tweepy.Client(
        consumer_key=X_CRED["consumer_key"],
        consumer_secret=X_CRED["consumer_secret"],
        access_token=X_CRED["access_token"],
        access_token_secret=X_CRED["access_token_secret"],
        wait_on_rate_limit=True
    )
    auth_v1 = tweepy.OAuth1UserHandler(
        X_CRED["consumer_key"], X_CRED["consumer_secret"],
        X_CRED["access_token"], X_CRED["access_token_secret"]
    )
    api_v1 = tweepy.API(auth_v1)
    # التحقق من الصلاحيات
    bot_info = client_v2.get_me()
    BOT_ID = bot_info.data.id
    logger.success(f"✅ تم الاتصال! أهلاً ناصر، البوت {bot_info.data.username} جاهز.")
except Exception as e:
    logger.error(f"❌ فشل الاتصال: تأكد من صلاحيات Read/Write في X Portal: {e}")
    exit()

# ==========================================
# المصادر (قنوات يوتيوب وأخبار)
# ==========================================
YT_CHANNELS = [
    "https://www.youtube.com/@Omardizer/shorts",
    "https://www.youtube.com/@AITNews/shorts",
    "https://www.youtube.com/@MarquesBrownlee/shorts"
]

RSS_FEEDS = [
    "https://aitnews.com/feed/",
    "https://www.tech-wd.com/wd/feed/"
]

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (أيبكس)
# ==========================================
async def ai_guard(prompt, context_type="news"):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    
    sys_msg = f"""أنت 'أيبكس'، خبير في الذكاء الاصطناعي وأحدث أدواته. 
    - المهمة: صياغة محتوى ({context_type}) للأفراد.
    - الأسلوب: لهجة خليجية بيضاء، احترافية، مشوقة.
    - الشروط: لا تستخدم كلمات إنجليزية وسط النص (ضعها بين أقواس فقط).
    - التنسيق: ابدأ بخطاف قوي، ثم الفائدة، ثم إيموجي.
    - إذا كان المحتوى غير مفيد تقنياً، رد بـ: SKIP"""

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ AI: {e}")
        return "SKIP"

# ==========================================
# 💬 محرك الردود الذكية (فاصل زمني بشري)
# ==========================================
async def process_interactions():
    logger.info("🔍 فحص المنشن للرد بذكاء...")
    try:
        mentions = client_v2.get_users_mentions(id=BOT_ID, max_results=5, tweet_fields=['author_id'])
        if not mentions.data: return

        for tweet in mentions.data:
            if tweet.author_id == BOT_ID: continue # منع الرد على النفس

            # محاكاة التفكير البشري (انتظار عشوائي)
            wait_time = random.randint(45, 180) 
            logger.info(f"⏳ انتظار {wait_time} ثانية قبل الرد على {tweet.id}...")
            await asyncio.sleep(wait_time)

            reply_text = await ai_guard(tweet.text, context_type="reply")
            if "SKIP" not in reply_text:
                client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                logger.success(f"✅ تم الرد على المنشن: {tweet.id}")

    except Exception as e:
        logger.error(f"❌ خطأ في محرك الردود: {e}")

# ==========================================
# 🎥 محرك الفيديو والأخبار
# ==========================================
def get_latest_video():
    target = random.choice(YT_CHANNELS)
    ydl_opts = {'quiet': True, 'extract_flat': False, 'playlist_items': '1'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                v = info['entries'][0]
                # تصحيح مشكلة تاريخ الرفع
                v_date = v.get('upload_date')
                if v_date:
                    upload_date = datetime.strptime(v_date, '%Y%m%d').replace(tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - upload_date) <= timedelta(hours=48):
                        return v
    except Exception as e: logger.error(f"🎥 خطأ فيديو: {e}")
    return None

async def get_latest_rss():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(random.choice(RSS_FEEDS), timeout=10)
            soup = BeautifulSoup(resp.content, 'xml') # استخدام lxml-xml
            item = soup.find('item')
            if item:
                return {"title": item.title.text, "link": item.link.text}
    except Exception as e: logger.error(f"📰 خطأ RSS: {e}")
    return None

# ==========================================
# 🚀 المحرك الرئيسي (Apex Engine)
# ==========================================
async def run_apex_engine():
    # 1. الردود أولاً
    await process_interactions()
    
    # 2. النشر الدوري
    logger.info("🎬 محاولة نشر محتوى جديد...")
    video = get_latest_video()
    if video:
        tweet_text = await ai_guard(video['title'], context_type="video")
        if "SKIP" not in tweet_text:
            video_file = "temp_video.mp4"
            ydl_opts = {'format': 'mp4', 'outtmpl': video_file, 'max_filesize': 15*1024*1024}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video['url']])
                media = api_v1.media_upload(filename=video_file, media_category='tweet_video')
                # انتظار معالجة الفيديو في X
                await asyncio.sleep(20)
                client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                logger.success("✅ تم نشر الفيديو!")
                return
            finally:
                if os.path.exists(video_file): os.remove(video_file)

    # بديل: نشر خبر RSS
    news = await get_latest_rss()
    if news:
        tweet_text = await ai_guard(news['title'], context_type="news")
        if "SKIP" not in tweet_text:
            client_v2.create_tweet(text=f"{tweet_text}\n\n🔗 {news['link']}")
            logger.success("✅ تم نشر الخبر!")

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
