import os
import asyncio
import httpx
import random
import datetime
import tweepy
import google.generativeai as genai
from loguru import logger

# =========================
# 🔐 إعدادات الهوية والأمان
# =========================
# نستخدم الأسماء اللي في ملف الـ YAML لضمان الربط
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
RAW_TG_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ضبط معرف تليجرام لضمان القبول
if RAW_TG_ID and not RAW_TG_ID.startswith("-100") and not RAW_TG_ID.startswith("@"):
    TG_CHAT_ID = f"-100{RAW_TG_ID}"
else:
    TG_CHAT_ID = RAW_TG_ID

# مفاتيح X (تويتر سابقاً)
X_KEYS = {
    "ck": os.getenv("X_API_KEY"),
    "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"),
    "ts": os.getenv("X_ACCESS_SECRET")
}

# إعداد محرك Google
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# =========================
# 🧠 صناعة المحتوى السيادي (Premium)
# =========================
def get_strategic_prompt():
    topics = [
        "استراتيجيات استخدام AI Agents لتوفير 20 ساعة عمل أسبوعياً للفرد",
        "مراجعة لأحدث أدوات الذكاء الاصطناعي وأحدث أدواته التي أطلقت هذا الأسبوع",
        "كيف تبني منظومة تقنية متكاملة (Personal AI Stack) في 2026",
        "تحويل المهام الروتينية إلى أتمتة كاملة باستخدام أدوات الذكاء الحديثة"
    ]
    return f"""
أنت 'أيبكس' المحرك التقني، اكتب مقالاً طويلاً وفخماً (Premium Long Post) لمنصة X.
الموضوع: {random.choice(topics)}
القواعد:
1. اللغة: خليجية بيضاء (فصحى مبسطة).
2. التنسيق: عنوان، مقدمة، نقاط عملية، وخاتمة.
3. القيمة: ركز على 'الذكاء الاصطناعي وأحدث أدواته' وكيف يستفيد الفرد منها فوراً.
4. الطول: استغل مساحة الاشتراك (أكثر من 3000 حرف).
"""

async def generate_content():
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(get_strategic_prompt())
        return response.text.strip()
    except Exception as e:
        logger.error(f"⚠️ فشل Gemini: {e}")
        return None

# =========================
# 📤 قنوات النشر (X & Telegram)
# =========================
def post_to_x(content):
    if not all(X_KEYS.values()):
        logger.warning("🔐 مفاتيح X غير مكتملة")
        return
    try:
        # استخدام Tweepy Client (v2) للمنشورات الطويلة
        client = tweepy.Client(
            consumer_key=X_KEYS["ck"],
            consumer_secret=X_KEYS["cs"],
            access_token=X_KEYS["at"],
            access_token_secret=X_KEYS["ts"]
        )
        # نشر المقال الطويل (ميزة بريميوم)
        client.create_tweet(text=content[:24000]) 
        logger.success("✅ تم نشر المقال الطويل في X")
    except Exception as e:
        logger.error(f"❌ فشل X: {e}")

async def post_to_tg(content):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        # تليجرام حده 4096 حرف، نقص المحتوى لو زاد
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": f"<b>🚀 أيبكس | القيمة المضافة</b>\n\n{content[:4000]}",
            "parse_mode": "HTML"
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                logger.success("✅ تم النشر في تليجرام")
    except Exception as e:
        logger.error(f"❌ فشل تليجرام: {e}")

# =========================
# 🔄 المشغل الرئيسي
# =========================
async def main():
    logger.info("🔥 انطلاق أيبكس (أقصى قدرة بريميوم)...")
    content = await generate_content()
    if content:
        post_to_x(content)
        await post_to_tg(content)
    logger.info("🏁 تمت المهمة.")

if __name__ == "__main__":
    asyncio.run(main())
