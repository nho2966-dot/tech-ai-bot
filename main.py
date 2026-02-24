import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
from loguru import logger
import tweepy
import yt_dlp
from openai import OpenAI
from dotenv import load_dotenv

# تحميل الإعدادات المحلية (إن وجدت)
load_dotenv()

# ==========================================
# ⚙️ الإعدادات والمفاتيح
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# الاتصال بمنصة X (نحتاج V1 لرفع الفيديو، و V2 لنشر التغريدة)
try:
    client_v2 = tweepy.Client(**X_CRED)
    auth_v1 = tweepy.OAuth1UserHandler(
        X_CRED["consumer_key"], 
        X_CRED["consumer_secret"], 
        X_CRED["access_token"], 
        X_CRED["access_token_secret"]
    )
    api_v1 = tweepy.API(auth_v1)
    logger.success("✅ تم الاتصال بمنصة X بنجاح")
except Exception as e:
    logger.error(f"❌ فشل الاتصال بمنصة X: {e}")

# القنوات التقنية المستهدفة (Shorts لضمان الحجم المناسب للفيديو)
YT_CHANNELS = [
    "https://www.youtube.com/@Omardizer/shorts",
    "https://www.youtube.com/@OsamaOfficial/shorts",
    "https://www.youtube.com/@Mrwhosetheboss/shorts",
    "https://www.youtube.com/@MarquesBrownlee/shorts"
]

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (الصياغة)
# ==========================================
async def ai_guard(prompt):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
    
    sys_msg = """أنت محرر تقني خبير في منصة 'أيبكس'. مهمتك صياغة تغريدة لفيديو تقني.
    - اللغة: عربية فصحى تقنية رصينة.
    - القيود: ممنوع استخدام كلمات إنجليزية داخل النص العربي (استخدم البديل العربي أو أبقِ اسم التقنية فقط بالإنجليزية).
    - الصرامة: لا تضف أي معلومة غير موجودة في المصدر.
    - التنسيق: خطاف مشوق + شرح الفائدة + إيموجي مناسب + لا تتجاوز 250 حرفاً.
    إذا كان المحتوى تافهاً، رد بكلمة واحدة فقط: SKIP"""

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ في محرك الذكاء الاصطناعي: {e}")
        return "SKIP"

# ==========================================
# 🎥 محرك جلب الفيديو
# ==========================================
def get_latest_video():
    target = random.choice(YT_CHANNELS)
    logger.info(f"🔍 فحص القناة: {target}")
    
    ydl_opts = {'quiet': True, 'extract_flat': True, 'playlist_items': '1'}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                v = info['entries'][0]
                upload_date = datetime.strptime(v['upload_date'], '%Y%m%d').replace(tzinfo=timezone.utc)
                
                # التأكد أن الفيديو جديد (خلال آخر 48 ساعة)
                if (datetime.now(timezone.utc) - upload_date) <= timedelta(hours=48):
                    return v
                else:
                    logger.warning("⏳ الفيديو المكتشف قديم (تجاوز 48 ساعة).")
    except Exception as e:
        logger.error(f"❌ فشل جلب الفيديو: {e}")
    return None

# ==========================================
# 🚀 المهمة الرئيسية: دورة أيبكس
# ==========================================
async def run_apex_engine():
    logger.info("🎬 محاولة العثور على فيديو تقني حديث...")
    video = get_latest_video()
    
    if video:
        prompt = f"العنوان: {video['title']}\nالوصف: {video.get('description', 'فيديو تقني جديد')}"
        tweet_text = await ai_guard(prompt)
        
        if "SKIP" not in tweet_text:
            video_file = "apex_video.mp4"
            # إعدادات التحميل: أفضل جودة لا تتجاوز 15 ميجا لضمان الرفع السلس على X
            ydl_opts = {
                'format': 'best[ext=mp4][filesize<15M]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                'outtmpl': video_file,
                'quiet': True
            }
            
            try:
                logger.info(f"📥 جاري تحميل الفيديو: {video['title']}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video['url']])
                
                logger.info("📤 جاري الرفع إلى منصة X (قد يستغرق بعض الوقت)...")
                media = api_v1.media_upload(filename=video_file, media_category='tweet_video')
                
                logger.info("⏳ انتظار معالجة الفيديو في سيرفرات X (30 ثانية)...")
                await asyncio.sleep(30)
                
                logger.info("📝 جاري نشر التغريدة...")
                client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                logger.success("✅ تم نشر الفيديو بنجاح على أيبكس!")
                
            except Exception as e:
                logger.error(f"❌ خطأ أثناء رفع/نشر الفيديو: {e}")
            finally:
                if os.path.exists(video_file):
                    os.remove(video_file)
                    logger.info("🗑️ تم تنظيف ملف الفيديو المؤقت.")
        else:
            logger.warning("⚠️ الذكاء الاصطناعي رفض المحتوى (SKIP).")
    else:
        logger.warning("📰 لم يتم العثور على فيديو حديث مطابق للشروط.")

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
