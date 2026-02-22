import os
import asyncio
import httpx
import random
import tweepy
from google import genai  # المكتبة الأحدث لعام 2026
from loguru import logger

# =========================
# 🔐 إدارة الهوية والأمان
# =========================
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
# معالجة معرف التليجرام لضمان القبول
RAW_TG_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TG_CHAT_ID = f"-100{RAW_TG_ID}" if RAW_TG_ID and not (RAW_TG_ID.startswith("-100") or RAW_TG_ID.startswith("@")) else RAW_TG_ID

# مفاتيح X بريميوم
X_CREDENTIALS = {
    "ck": os.getenv("X_API_KEY"),
    "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"),
    "ts": os.getenv("X_ACCESS_SECRET")
}

# =========================
# 🧠 محرك "أيبكس" لصناعة المحتوى
# =========================
async def generate_premium_content():
    try:
        # إعداد عميل Google GenAI الجديد
        client = genai.Client(api_key=GEMINI_KEY)
        
        prompt = """
        اكتب مقالاً تقنياً فخماً ومطولاً (Premium Long Post) بلهجة خليجية بيضاء.
        الموضوع: 'الذكاء الاصطناعي وأحدث أدواته' وكيف يمكن للأفراد استخدامه لزيادة دخلهم وإنتاجيتهم.
        ركز على أدوات أطلقت في 2026. استخدم نقاط واضحة وعنواناً جذاباً.
        تجنب الرسميات الزائدة، كن كأنك خبير تقني يتحدث لصديقه (ناصر).
        """
        
        # استخدام موديل 2.0 Flash الأحدث
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"❌ خطأ في محرك الذكاء الاصطناعي: {e}")
        return None

# =========================
# 📤 قنوات النشر (X & Telegram)
# =========================
def post_to_x(content):
    if not all(X_CREDENTIALS.values()):
        logger.warning("🔐 مفاتيح X غير مكتملة في الإعدادات")
        return
    try:
        # استخدام API v2 للنشر (يدعم المقالات الطويلة)
        client = tweepy.Client(
            consumer_key=X_CREDENTIALS["ck"],
            consumer_secret=X_CREDENTIALS["cs"],
            access_token=X_CREDENTIALS["at"],
            access_token_secret=X_CREDENTIALS["ts"]
        )
        client.create_tweet(text=content[:24500]) # دعم مساحة البريميوم
        logger.success("✅ تم النشر في X بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في X: {e}")

async def post_to_telegram(content):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            payload = {
                "chat_id": TG_CHAT_ID,
                "text": f"<b>🚀 أيبكس | جديد الأدوات</b>\n\n{content[:4000]}",
                "parse_mode": "HTML"
            }
            await client.post(url, json=payload)
        logger.success("✅ تم النشر في تليجرام")
    except Exception as e:
        logger.error(f"❌ خطأ تليجرام: {e}")

# =========================
# 🔄 المشغل الأساسي
# =========================
async def main():
    logger.info("🔥 تشغيل أيبكس بأحدث التقنيات 2026...")
    
    if not GEMINI_KEY:
        logger.critical("🔑 GEMINI_KEY غير موجود!")
        return

    content = await generate_premium_content()
    if content:
        # النشر المتوازي
        post_to_x(content)
        await post_to_telegram(content)
    
    logger.info("🏁 انتهت الجولة.")

if __name__ == "__main__":
    asyncio.run(main())
