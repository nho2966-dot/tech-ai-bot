import os, asyncio, httpx, random, datetime, tweepy
from loguru import logger

# =========================
# 🔐 الإعدادات
# =========================
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
RAW_TG_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TG_CHAT_ID = f"-100{RAW_TG_ID}" if RAW_TG_ID and not RAW_TG_ID.startswith(("-100", "@")) else RAW_TG_ID

X_KEYS = {
    "ck": os.getenv("X_API_KEY"),
    "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"),
    "ts": os.getenv("X_ACCESS_SECRET")
}

# =========================
# 🧠 محرك المحتوى البريميوم
# =========================
def get_ultra_premium_prompt():
    topics = [
        "دليل عملي لربط AI Agents بمهامك اليومية لزيادة إنتاجيتك 10 أضعاف",
        "تحليل لأقوى أدوات الذكاء الاصطناعي وأحدث أدواته التي أطلقت هذا الأسبوع",
        "كيف تبني نظام أتمتة شخصي متكامل بدون كود (No-Code AI Suite)",
        "مستقبل السيادة التقنية للأفراد في ظل تطور الذكاء الاصطناعي"
    ]
    return f"""اكتب مقالاً طويلاً (Premium Long-Form) لمنصة X عن: {random.choice(topics)}.
    المتطلبات: عنوان قوي، مقدمة، شرح تفصيلي لـ 3 أدوات على الأقل، خطوات عملية، وخاتمة.
    اللغة: خليجية احترافية. اذكر 'الذكاء الاصطناعي وأحدث أدواته'. الطول: استغل مساحة 4000 حرف."""

async def generate_ultra_content():
    if not GEMINI_KEY: return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": get_ultra_premium_prompt()}]}]}
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                logger.error(f"❌ Gemini Error: {r.status_code} - {r.text}")
    except Exception as e: 
        logger.error(f"⚠️ خطأ محرك الذكاء: {e}")
    return None

# =========================
# 📤 النشر السيادي في X
# =========================
def check_x_keys():
    """تحقق من صلاحية مفاتيح X قبل النشر"""
    if not all(X_KEYS.values()): 
        logger.warning("⚠️ مفاتيح X غير مكتملة")
        return None
    try:
        client = tweepy.Client(X_KEYS["ck"], X_KEYS["cs"], X_KEYS["at"], X_KEYS["ts"])
        # اختبار وصول محدود
        client.get_user(username="any")  
        return client
    except tweepy.errors.Forbidden:
        logger.warning("⚠️ مفاتيح X غير صالحة أو صلاحيات محدودة")
        return None
    except Exception as e:
        logger.error(f"⚠️ خطأ عند التحقق من مفاتيح X: {e}")
        return None

def post_to_x_premium(content):
    client = check_x_keys()
    if not client:
        logger.info("⏩ تجاوز النشر في X بسبب مشاكل المفاتيح")
        return
    try:
        # تقطيع المحتوى حسب الاشتراك: Free < 280، Pro < 5000، Enterprise < 24500
        max_len = 24500  
        res = client.create_tweet(text=content[:max_len])
        logger.success(f"✅ تم نشر المقال في X بنجاح! ID: {res.data['id']}")
    except tweepy.errors.Forbidden as e:
        logger.error(f"❌ رفض X: {e}")
    except Exception as e:
        logger.error(f"❌ خطأ X: {e}")

# =========================
# 📤 النشر في Telegram
# =========================
async def post_to_tg_premium(content):
    if not TG_TOKEN or not TG_CHAT_ID: 
        logger.warning("⚠️ بيانات تليجرام غير مكتملة")
        return
    try:
        msg = f"<b>🚀 أيبكس | القيمة المضافة</b>\n\n{content}"
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                json={"chat_id": TG_CHAT_ID, "text": msg[:4090], "parse_mode": "HTML"}
            )
            if r.status_code == 200: logger.success("✅ تم النشر في تليجرام")
            else: logger.error(f"❌ تليجرام رفض: {r.text}")
    except Exception as e: logger.error(f"❌ عطل تليجرام: {e}")

# =========================
# 🔄 المشغل الرئيسي
# =========================
async def main():
    logger.info("🔥 تشغيل محرك أيبكس (أقصى قدرة بريميوم)...")
    content = await generate_ultra_content()
    if content:
        post_to_x_premium(content)
        await post_to_tg_premium(content)
    else:
        logger.warning("⚠️ لم يتم توليد محتوى للنشر")
    logger.info("🏁 تمت المهمة.")

if __name__ == "__main__":
    asyncio.run(main())
