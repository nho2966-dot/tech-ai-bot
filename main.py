import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
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

# --- 🛡️ الفلتر الصارم (ناصر) ---
def nasser_filter(text):
    if not text: return ""
    # استبدال المصطلحات حسب الرغبة
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    return text.strip()

# --- 🧠 نظام العقول المحدث (Fixing 404 & 429) ---
async def ask_multiple_brains(prompt, system_msg):
    # مسميات دقيقة تتوافق مع v1beta و v1
    models = [
        "gemini-2.0-flash", 
        "gemini-1.5-flash-latest", 
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest"
    ]
    
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": f"{system_msg}\n\n{prompt}"}]}]}
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                logger.info(f"🔄 جاري استشارة: {model_name}")
                r = await client.post(url, json=payload)
                data = r.json()
                
                if 'candidates' in data:
                    res_text = data['candidates'][0]['content']['parts'][0]['text']
                    return nasser_filter(res_text)
                
                elif 'error' in data:
                    err_code = data['error'].get('code')
                    if err_code == 429: # زحمة كوتا
                        logger.warning(f"⏳ {model_name} عليه زحمة، بننتظر شوي وننقل للي بعده..")
                        await asyncio.sleep(5) # انتظار بسيط قبل المحاولة التالية
                    elif err_code == 404:
                        logger.warning(f"🚫 {model_name} غير متاح في هذا الإصدار، نجرب غيره..")
                    else:
                        logger.error(f"❌ خطأ {err_code}: {data['error'].get('message')}")
        except Exception as e:
            logger.error(f"🔥 عطل فني في {model_name}: {e}")
            
    return None

# --- 📡 رادار الميديا ---
async def fetch_visuals():
    if not PEXELS_KEY: return None
    headers = {"Authorization": PEXELS_KEY}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.pexels.com/videos/search?query=tech&per_page=1&orientation=portrait", headers=headers)
            v_data = r.json().get('videos', [])
            if v_data:
                v_url = v_data[0]['video_files'][0]['link']
                v_res = await client.get(v_url)
                with open("media.mp4", "wb") as f: f.write(v_res.content)
                return "media.mp4"
    except: return None

# --- 🚀 التشغيل ---
async def main():
    logger.info("🤖 نظام ناصر 'متعدد العقول' V2 قيد التشغيل...")
    
    sys_msg = "أنت ناصر، خبير تقني خليجي ذكي. لهجتك كويتية/سعودية بيضاء. ركز على أدوات AI للأفراد فقط."
    prompt = "عطني أداة ذكاء اصطناعي جديدة خرافية تهم الأفراد هالأيام."
    
    content = await ask_multiple_brains(prompt, sys_msg)
    
    if content:
        media = await fetch_visuals()
        try:
            if media:
                m_id = api_v1.media_upload(filename=media).media_id
                client_v2.create_tweet(text=content, media_ids=[m_id])
            else:
                client_v2.create_tweet(text=content)
            logger.success("✅ تم النشر بنجاح!")
        except Exception as e:
            logger.error(f"❌ فشل X: {e}")
        finally:
            if media and os.path.exists(media): os.remove(media)
    else:
        logger.critical("🚨 تعطلت كل المحاولات، قوقل مقفلين الكوتا بالكامل حالياً.")

if __name__ == "__main__":
    asyncio.run(main())
