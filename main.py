import os
import asyncio
import random
from datetime import datetime, timezone
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

client_v2 = tweepy.Client(**X_CRED)
auth_v1 = tweepy.OAuth1UserHandler(X_CRED["consumer_key"], X_CRED["consumer_secret"], X_CRED["access_token"], X_CRED["access_token_secret"])
api_v1 = tweepy.API(auth_v1)

# المصادر الموثوقة (Whitelisted Only)
RSS_FEEDS = ["https://aitnews.com/feed/", "https://www.tech-wd.com/wd/feed/", "https://www.unlimit-tech.com/feed/"]
YT_CHANNELS = [
    "https://www.youtube.com/@MarquesBrownlee/shorts",
    "https://www.youtube.com/@Mrwhosetheboss/shorts",
    "https://www.youtube.com/@OsamaOfficial/shorts",
    "https://www.youtube.com/@Omardizer/shorts"
]

# ==========================================
# 🛡️ نظام منع الهلوسة والفلترة
# ==========================================
async def ai_guard(prompt, system_instruction):
    """محرك الذكاء الاصطناعي مع قيود صارمة لمنع الهلوسة"""
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
            temperature=0.1 # تقليل الإبداع لزيادة الدقة (منع الهلوسة)
        )
        return response.choices[0].message.content.strip()
    except: return "SKIP"

# ==========================================
# 🔍 محركات جلب المحتوى (أخبار + فيديو)
# ==========================================
async def get_latest_news():
    async with httpx.AsyncClient() as client:
        r = await client.get(random.choice(RSS_FEEDS), timeout=15)
        soup = BeautifulSoup(r.content, "xml")
        item = soup.find('item')
        if item:
            return {"title": item.title.text, "link": item.link.text, "desc": item.description.text[:500]}
    return None

def get_latest_video():
    ydl_opts = {'quiet': True, 'extract_flat': True, 'playlist_items': '1'}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(random.choice(YT_CHANNELS), download=False)
            video = info['entries'][0]
            # شرط الحداثة: 48 ساعة
            if video.get('upload_date'):
                upload_date = datetime.strptime(video['upload_date'], '%Y%m%d').replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - upload_date).days <= 2:
                    return video
    except: return None
    return None

# ==========================================
# 📤 محرك النشر الذكي والتنوع
# ==========================================
async def run_apex_engine():
    dice = random.random()
    logger.info(f"🎲 النسبة المحققة: {dice:.2f}")

    # 1. مسار الفيديو (35%)
    if dice < 0.35:
        video = get_latest_video()
        if video:
            sys_msg = "أنت رقيب محتوى. إذا كان الفيديو تقنياً ومفيداً وأخلاقياً، صغ تغريدة مشوقة. إذا كان غير ذلك اكتب SKIP."
            content = await ai_guard(f"العنوان: {video['title']}\nالرابط: {video['url']}", sys_msg)
            if "SKIP" not in content:
                # تحميل ونشر الفيديو (نفس الكود السابق)
                path = "temp_v.mp4"
                with yt_dlp.YoutubeDL({'format': 'mp4', 'outtmpl': path, 'max_filesize': 15*1024*1024}) as ydl:
                    ydl.download([video['url']])
                media = api_v1.media_upload(filename=path, media_category='tweet_video')
                await asyncio.sleep(20) # انتظار المعالجة
                client_v2.create_tweet(text=content[:280], media_ids=[media.media_id])
                os.remove(path)

    # 2. مسار الأخبار والثريدات (65%)
    else:
        news = await get_latest_news()
        if news:
            sys_msg = """أنت محرر تقني. 
            - امنع الهلوسة: لا تضف أي معلومة غير موجودة في النص.
            - الفلترة: ارفض أخبار التمويل والأرباح.
            - التنوع: اختر عشوائياً بين (تغريدة عادية، استطلاع رأي POLL، أو ثريد 1/3).
            - التنسيق: سطر فارغ بين الجمل + إيموجي تقني.
            إذا كان الخبر غير مهم للمتابع اكتب SKIP."""
            
            content = await ai_guard(f"الخبر: {news['title']}\nالتفاصيل: {news['desc']}\nالمصدر: {news['link']}", sys_msg)
            
            if "SKIP" not in content:
                if "POLL:" in content: # استطلاع رأي
                    parts = content.split("POLL:")
                    opts = [o.strip()[:25] for o in parts[1].split(",")][:4]
                    client_v2.create_tweet(text=parts[0][:280], poll_options=opts, poll_duration_minutes=1440)
                elif "1/3" in content: # ثريد
                    tweets = [t.strip() for t in content.split("\n\n") if len(t) > 5]
                    last_id = None
                    for t in tweets[:3]:
                        res = client_v2.create_tweet(text=t[:280], in_reply_to_tweet_id=last_id)
                        last_id = res.data['id']
                        await asyncio.sleep(random.randint(20, 40)) # فاصل بشري
                else: # تغريدة عادية
                    client_v2.create_tweet(text=content[:280])

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
