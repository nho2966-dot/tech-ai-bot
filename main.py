import os, asyncio, httpx, random, datetime, tweepy
from loguru import logger

# =========================
# 🔐 إعدادات الهوية والأمان
# =========================
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
RAW_TG_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ضبط الـ Chat ID لضمان قبول القنوات الخاصة
if RAW_TG_ID and not RAW_TG_ID.startswith("-100") and not RAW_TG_ID.startswith("@"):
    TG_CHAT_ID = f"-100{RAW_TG_ID}"
else:
    TG_CHAT_ID = RAW_TG_ID

# مفاتيح X (OAuth1.0a كاملة للكتابة + دعم Super Follows)
X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# =========================
# 🧠 محرك صناعة المحتوى (أيبكس)
# =========================
def get_strictly_fresh_prompt():
    topics = [
        "أدوات الذكاء الاصطناعي الشخصية (AI Agents) في 2026",
        "كيف تغير أجهزة الذكاء الاصطناعي القابلة للارتداء حياتنا اليومية",
        "أتمتة المهام المنزلية والعملية باستخدام Artificial Intelligence and its latest tools",
        "نصائح ذهبية للفرد لاستخدام الـ AI في تنظيم الوقت والإنتاجية"
    ]
    current_moment = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
أنت 'أيبكس' الخبير التقني، اكتب ثريد خليجي احترافي من 3 تغريدات عن: {random.choice(topics)}.
القواعد الصارمة:
1. اللغة: خليجية بيضاء (فصحى مبسطة بلهجة تقنية).
2. افصل بين كل تغريدة وأخرى بـ [SPLIT].
3. المحتوى حصري لعام 2026 وغير مكرر.
4. التزم بذكر 'الذكاء الاصطناعي وأحدث أدواته' بدلاً من الثورة الصناعية.
5. سياق الوقت: {current_moment}.
"""

async def generate_content():
    # محاولة Gemini أولاً
    if GEMINI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            payload = {
                "contents": [{"parts": [{"text": get_strictly_fresh_prompt()}]}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    parts = [p.strip() for p in text.split("[SPLIT]") if p.strip()]
                    if len(parts) >= 2:
                        parts[-1] += f"\n\n🔖 {random.getrandbits(16):x}"
                        return parts
        except Exception as e:
            logger.error(f"⚠️ تعثر Gemini: {e}")

    # محتوى الطوارئ في حال فشل الـ APIs
    return [
        f"عالم الذكاء الاصطناعي في 2026 يتطور بجنون 🚀\n{datetime.datetime.now().second}",
        "أدواتك الشخصية صارت أذكى وتنفذ مهامك عنك 🎯",
        f"تابع أيبكس لكل جديد في عالم التقنية 🔥\nID: {random.randint(100,999)}"
    ]

# =========================
# 📤 قنوات النشر
# =========================
def post_to_x(content):
    """نشر الثريد في X مع دعم Super Follows"""
    try:
        # استخدام OAuth1.0a لتفادي خطأ 401
        auth = tweepy.OAuth1UserHandler(X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S)
        api = tweepy.API(auth, wait_on_rate_limit=True)
        last_id = None

        for idx, part in enumerate(content):
            # التحقق من طول التغريدة
            tweet = api.update_status(status=part[:280], in_reply_to_status_id=last_id,
                                      auto_populate_reply_metadata=True)
            last_id = tweet.id

            # مثال على إضافة محتوى للـ Super Followers (اختياري)
            if idx == 0:  # أول تغريدة يمكن تحديدها لمتابعي الاشتراك
                try:
                    api.create_super_follow_only_tweet(tweet.id)
                    logger.info("💎 تم تفعيل النشر لمتابعي الاشتراك Super Follows")
                except Exception as e:
                    logger.warning(f"⚠️ لم يتم تفعيل Super Follows: {e}")

        logger.success("✅ تم نشر الثريد في X بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ X: {e}")

async def post_to_tg(content):
    """نشر في Telegram بشكل جذاب"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        formatted_text = "🧵 <b>ثريد أيبكس التقني</b>\n" + "—" * 15 + "\n\n"
        formatted_text += "\n\n🔹 ".join(content)

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json={
                "chat_id": TG_CHAT_ID,
                "text": formatted_text,
                "parse_mode": "HTML"
            })
            if r.status_code == 200:
                logger.success("✅ تم النشر في تليجرام")
            else:
                logger.error(f"❌ تليجرام رفض: {r.text}")
    except Exception as e:
        logger.error(f"❌ عطل تليجرام: {e}")

# =========================
# 🔄 المشغل الرئيسي
# =========================
async def main():
    logger.info("🚀 محرك أيبكس في وضع الاستعداد...")
    content = await generate_content()
    post_to_x(content)
    await post_to_tg(content)
    logger.info("🏁 تمت المهمة بنجاح.")

if __name__ == "__main__":
    asyncio.run(main())
