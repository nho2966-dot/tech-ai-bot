import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
from datetime import datetime
from loguru import logger

# --- 🔐 الإعدادات ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

# إعداد X
auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(bearer_token=X_CREDS["bearer"], consumer_key=X_CREDS["key"], 
                          consumer_secret=X_CREDS["secret"], access_token=X_CREDS["token"], 
                          access_token_secret=X_CREDS["access_s"])

# --- 🛡️ نظام الفلترة (شرط ناصر) ---
def nasser_filter(text):
    if not text: return ""
    return text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته").strip()

# --- 🧠 نظام العقول المتعددة (Fallback System) ---
async def ask_multiple_brains(prompt, system_msg):
    # قائمة العقول المتاحة (بالترتيب من الأحدث للأكثر استقراراً)
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"System: {system_msg}\nUser: {prompt}"}]}]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                logger.info(f"🧠 محاولة استشارة العقل: {model_name}")
                r = await client.post(url, json=payload)
                data = r.json()
                
                if 'candidates' in data:
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    return nasser_filter(text)
                elif 'error' in data and data['error']['code'] == 429:
                    logger.warning(f"⚠️ العقل {model_name} مشغول (Quota Exceeded)، ننتقل للتالي...")
                    continue # جرب الموديل اللي بعده
                else:
                    logger.error(f"❌ خطأ غير متوقع في {model_name}: {data}")
        except Exception as e:
            logger.error(f"🔥 تعطل العقل {model_name}: {e}")
            continue
            
    return None

# --- 📡 رادار الميديا المطور ---
async def fetch_visuals():
    if not PEXELS_KEY: return None, None
    headers = {"Authorization": PEXELS_KEY}
    query = random.choice(["AI technology", "future tech", "coding robot"])
    
    try:
        async with httpx.AsyncClient() as client:
            # محاولة فيديو طولي
            v_res = await client.get(f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait", headers=headers)
            videos = v_res.json().get('videos', [])
            if videos:
                v_url = random.choice(videos)['video_files'][0]['link']
                content = await client.get(v_url)
                with open("media.mp4", "wb") as f: f.write(content.content)
                return "media.mp4", "video"
    except: pass
    return None, None

# --- 🚀 تشغيل البوت ---
async def main():
    logger.info("🚀 تشغيل نظام العقول المتعددة لناصر...")
    
    sys_msg = "أنت خبير تقني خليجي. اكتب بلهجة بيضاء ممتعة. ركز على أدوات AI للأفراد. لا تذكر 'الثورة الصناعية الرابعة'."
    prompt = "عطني أداة ذكاء اصطناعي خرافية للأفراد تسهل حياتهم، مع شرح سريع وفائدة."
    
    # استشارة العقول
    content = await ask_multiple_brains(prompt, sys_msg)
    
    if content:
        media_path, _ = await fetch_visuals()
        try:
            if media_path:
                m_id = api_v1.media_upload(filename=media_path).media_id
                client_v2.create_tweet(text=content, media_ids=[m_id])
            else:
                client_v2.create_tweet(text=content)
            logger.success("✅ تم النشر بنجاح بفضل نظام العقول المتعددة!")
        except Exception as e:
            logger.error(f"❌ فشل النشر: {e}")
        finally:
            if media_path and os.path.exists(media_path): os.remove(media_path)
    else:
        logger.critical("🚨 جميع العقول مشغولة حالياً، حاول لاحقاً.")

if __name__ == "__main__":
    asyncio.run(main())
