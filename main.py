import os
import json
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
import schedule

load_dotenv()

# ==========================================
# ⚙️ المفاتيح والإعدادات
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}
TG_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GIANTS_TO_SNIPE = ["44196397", "76837396"]  # إيلون ماسك، سام ألتمان
TIME_WINDOW_MINUTES = 130 # نافذة أكبر من الجدولة (ساعتين) لضمان عدم تفويت شيء

YT_CHANNELS = [
    "https://www.youtube.com/@Omardizer/shorts",
    "https://www.youtube.com/@OsamaOfficial/shorts",
    "https://www.youtube.com/@Mrwhosetheboss/shorts",
    "https://www.youtube.com/@MarquesBrownlee/shorts",
    "https://www.youtube.com/@AITNews/shorts"
]

RSS_FEEDS = [
    "https://aitnews.com/feed/",
    "https://www.tech-wd.com/wd/feed/"
]

DB_FILE = "apex_db.json"

# ==========================================
# 🛡️ نظام الذاكرة (لمنع التكرار والهلوسة)
# ==========================================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"replied_tweets": []}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

async def send_tg_alert(message):
    if TG_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚠️ تنبيه أيبكس:\n{message}"})
        except Exception as e:
            logger.error(f"فشل إرسال لتيليجرام: {e}")

# ==========================================
# 📱 الاتصال بمنصة X
# ==========================================
try:
    client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
    auth_v1 = tweepy.OAuth1UserHandler(
        X_CRED["consumer_key"], X_CRED["consumer_secret"],
        X_CRED["access_token"], X_CRED["access_token_secret"]
    )
    api_v1 = tweepy.API(auth_v1)
    logger.success("✅ تم الاتصال بمنصة X بنجاح")
except Exception as e:
    logger.error(f"❌ فشل الاتصال بمنصة X: {e}")
    asyncio.run(send_tg_alert(f"فشل تسجيل الدخول لـ X: {e}"))

# ==========================================
# 🧠 الذكاء الاصطناعي – صياغة خليجية
# ==========================================
async def ai_guard(prompt, context_type="post"):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    
    if context_type == "reply":
        sys_msg = """أنت 'أيبكس'، خبير تقني رصين. رد على هذا المحتوى بأسلوب احترافي يفيد الأفراد.
- اللغة: لهجة خليجية بيضاء.
- القيود: ممنوع الهلوسة، ممنوع استخدام الرموز، ممنوع اللغات غير العربية (عدا أسماء التقنيات بين أقواس).
- الطول: جملة أو جملتين بالكثير.
إذا كان المحتوى لا يستحق الرد، أرسل: SKIP"""
    else:
        sys_msg = f"""أنت 'أيبكس'، خبير تقني رصين. صغ هذا المحتوى ليكون مفيداً للأفراد ويركز على أحدث أدوات الذكاء الاصطناعي.
- اللغة: لهجة خليجية بيضاء ومفهومة.
- القيود: صفر هلوسة، لا تستخدم الرموز، ولا لغات أجنبية (فقط الأسماء بين أقواس).
- الطول: مكثف ولا يتجاوز 250 حرف.
- التنسيق: خطاف مشوق + شرح الفائدة + إيموجي.
إذا كان المحتوى ضعيفاً، أرسل: SKIP"""
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":sys_msg},{"role":"user","content":prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ في الذكاء الاصطناعي: {e}")
        return "SKIP"

# ==========================================
# 🎥 فيديوهات YouTube & 📰 أخبار RSS
# ==========================================
def get_latest_video():
    target = random.choice(YT_CHANNELS)
    ydl_opts = {'quiet': True, 'extract_flat': True, 'playlist_items': '1'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                v = info['entries'][0]
                upload_date = datetime.strptime(v['upload_date'], '%Y%m%d').replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - upload_date) <= timedelta(hours=48):
                    return v
    except Exception as e:
        logger.error(f"❌ فشل جلب الفيديو: {e}")
    return None

async def get_latest_rss():
    target_feed = random.choice(RSS_FEEDS)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_feed, timeout=15)
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        if items:
            return {"title": items[0].title.text, "link": items[0].link.text}
    except Exception as e:
        logger.error(f"❌ فشل جلب الأخبار: {e}")
    return None

# ==========================================
# 💬 التفاعل الذكي (منشنات وقنص العمالقة)
# ==========================================
async def process_interactions(bot_id, time_limit):
    db = load_db()
    
    # 1. الرد على المنشنات
    try:
        mentions = client_v2.get_users_mentions(id=bot_id, max_results=5, tweet_fields=["created_at"])
        if mentions and mentions.data:
            for m in mentions.data:
                if m.created_at > time_limit and str(m.id) not in db["replied_tweets"]:
                    reply = await ai_guard(m.text, "reply")
                    if reply != "SKIP":
                        client_v2.create_tweet(text=reply, in_reply_to_tweet_id=m.id)
                        db["replied_tweets"].append(str(m.id))
                        logger.success(f"✅ تم الرد على المنشن {m.id}")
                        await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"❌ خطأ في المنشن: {e}")

    # 2. Sniper Mode (قنص العمالقة)
    for giant_id in GIANTS_TO_SNIPE:
        try:
            tweets = client_v2.get_users_tweets(id=giant_id, max_results=5, exclude=["retweets","replies"], tweet_fields=["created_at"])
            if tweets and tweets.data:
                latest = tweets.data[0]
                if latest.created_at > time_limit and str(latest.id) not in db["replied_tweets"]:
                    reply = await ai_guard(latest.text, "reply")
                    if reply != "SKIP":
                        client_v2.create_tweet(text=reply, in_reply_to_tweet_id=latest.id)
                        db["replied_tweets"].append(str(latest.id))
                        logger.success(f"🎯 تم قنص التغريدة للعملاق {giant_id}")
                        await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"❌ خطأ في قنص {giant_id}: {e}")
            
    # تنظيف الذاكرة القديمة وحفظها
    db["replied_tweets"] = db["replied_tweets"][-100:] 
    save_db(db)

# ==========================================
# 🚀 المهمة الرئيسية – دورة أيبكس
# ==========================================
async def run_apex_engine():
    now_utc = datetime.now(timezone.utc)
    time_limit = now_utc - timedelta(minutes=TIME_WINDOW_MINUTES)
    
    bot_info = client_v2.get_me()
    bot_id = bot_info.data.id

    logger.info("🎬 محاولة النشر الأساسي (فيديو/أخبار)...")
    video = get_latest_video()
    if video:
        prompt = f"العنوان: {video['title']}\nالوصف: {video.get('description','أداة ذكاء اصطناعي جديدة')}"
        tweet_text = await ai_guard(prompt, "post")
        if tweet_text != "SKIP":
            video_file = "apex_video.mp4"
            try:
                with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': video_file, 'max_filesize': 15*1024*1024}) as ydl:
                    ydl.download([video['url']])
                media = api_v1.media_upload(filename=video_file, media_category='tweet_video')
                await asyncio.sleep(30)
                client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                logger.success("✅ تم نشر الفيديو بنجاح")
            except Exception as e:
                logger.error(f"❌ خطأ أثناء رفع الفيديو: {e}")
            finally:
                if os.path.exists(video_file): os.remove(video_file)
    else:
        news_item = await get_latest_rss()
        if news_item:
            tweet_text = await ai_guard(news_item['title'], "post")
            if tweet_text != "SKIP":
                try:
                    client_v2.create_tweet(text=f"{tweet_text}\n\n🔗 {news_item['link']}")
                    logger.success("✅ تم نشر الخبر بنجاح")
                except Exception as e:
                    logger.error(f"❌ خطأ في نشر الخبر: {e}")

    logger.info("💬 بدء التفاعل والردود...")
    await process_interactions(bot_id, time_limit)
    logger.info("🏁 دورة البوت اكتملت بنجاح")

# ==========================================
# ⏰ الجدولة
# ==========================================
def start_cycle():
    asyncio.run(run_apex_engine())

if __name__ == "__main__":
    start_cycle() # تشغيل فوري أول مرة
    schedule.every(2).hours.do(start_cycle)
    logger.info("🚀 البوت يعمل تلقائيًا الآن وينتظر الجدولة...")
    while True:
        schedule.run_pending()
        time.sleep(30)
