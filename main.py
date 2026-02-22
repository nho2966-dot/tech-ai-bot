import os, asyncio, httpx, random, logging, tweepy
from loguru import logger

# =========================
# 🔐 إعدادات البيئة
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
# 🧠 محتوى البوت
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

# =========================
# 🔄 إدارة النماذج والأخطاء
# =========================
async def get_available_models():
    """إحضار النماذج المتاحة ودعمها لـ generateContent"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            models = r.json().get("models", [])
            # قائمة النماذج التي تدعم توليد المحتوى
            return [m["name"] for m in models if "generateContent" in m.get("supportedMethods", [])]
        except Exception as e:
            logger.error(f"❌ خطأ في جلب النماذج: {e}")
            return []

async def generate_ultra_content(retries=3):
    """توليد المحتوى مع ديناميكية التعامل مع الأخطاء"""
    models = await get_available_models()
    if not models:
        logger.warning("⚠️ لم يتم العثور على أي نموذج صالح")
        return None

    for attempt in range(retries):
        for model_name in models:
            try:
                logger.info(f"🔥 محاولة توليد محتوى باستخدام: {model_name} (Attempt {attempt+1})")
                payload = {"contents": [{"parts": [{"text": get_ultra_premium_prompt()}]}]}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                async with httpx.AsyncClient(timeout=45) as client:
                    r = await client.post(url, json=payload)
                    if r.status_code == 200:
                        content = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                        return content
                    else:
                        logger.warning(f"⚠️ نموذج {model_name} فشل: {r.status_code} - {r.text[:150]}")
            except Exception as e:
                logger.error(f"❌ خطأ أثناء استخدام النموذج {model_name}: {e}")
        await asyncio.sleep(2)  # تأخير قصير قبل إعادة المحاولة
    logger.error("❌ فشل كل النماذج بعد المحاولات المتعددة")
    return None

# =========================
# 📤 النشر
# =========================
def post_to_x_premium(content):
    if not X_KEYS["ck"]: return
    try:
        client = tweepy.Client(X_KEYS["ck"], X_KEYS["cs"], X_KEYS["at"], X_KEYS["ts"])
        res = client.create_tweet(text=content[:24500])
        logger.success(f"✅ تم نشر المقال في X بنجاح! ID: {res.data['id']}")
    except Exception as e: logger.error(f"❌ عطل في X: {e}")

async def post_to_tg_premium(content):
    if not TG_TOKEN: return
    try:
        msg = f"<b>🚀 أيبكس | القيمة المضافة</b>\n\n{content}"
        async with httpx.AsyncClient() as client:
            r = await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                                  json={"chat_id": TG_CHAT_ID, "text": msg[:4090], "parse_mode": "HTML"})
            if r.status_code == 200: logger.success("✅ تم النشر في تليجرام")
            else: logger.warning(f"⚠️ خطأ في تليجرام: {r.status_code}")
    except Exception as e: logger.error(f"❌ عطل تليجرام: {e}")

# =========================
# 🔝 المشغل الرئيسي
# =========================
async def main():
    logger.info("🔥 تشغيل محرك أيبكس الديناميكي...")
    content = await generate_ultra_content()
    if content:
        post_to_x_premium(content)
        await post_to_tg_premium(content)
    else:
        logger.warning("⚠️ لم يتم توليد محتوى للنشر")
    logger.info("🏁 المهمة اكتملت.")

if __name__ == "__main__":
    asyncio.run(main())
