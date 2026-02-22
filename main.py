import os, asyncio, httpx, random, datetime, tweepy
from loguru import logger

# =========================
# 🔐 إعدادات البريميوم
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
# 🧠 محرك القيمة المضافة القصوى
# =========================
def get_ultra_premium_prompt():
    # قائمة مواضيع "ذهبية" للفرد في 2026
    topics = [
        "خطوات بناء 'موظف رقمي' كامل يدير عملك الخاص باستخدام AI Agents",
        "تحليل عميق لأحدث 10 أدوات AI ظهرت هذا الأسبوع وكيف تستخدمها فوراً",
        "دليل الفرد للسيادة التقنية: كيف تحمي بياناتك وتضاعف إنتاجيتك في عصر الذكاء الاصطناعي",
        "استراتيجية الأتمتة الكاملة (Hyper-Automation) للمهام اليومية والمالية"
    ]
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"""
أنت 'أيبكس' المحرك السيادي، اكتب مقالاً طويلاً (Premium Long-Form) لمنصة X.
الموضوع: {random.choice(topics)}
التوقيت: {current_time}

المتطلبات لتعظيم القيمة:
1. العناوين: استخدم عناوين رئيسية وفرعية واضحة.
2. التفاصيل: ادخل في صلب 'كيفية التنفيذ' وليس فقط 'ما هو'.
3. الأدوات: اذكر أسماء أدوات محددة (مثل Cursor, Replit, AutoGPT) وكيفية الربط بينها.
4. اللغة: خليجية بيضاء، احترافية، ممتعة.
5. المصطلح الثابت: استخدم 'الذكاء الاصطناعي وأحدث أدواته'.
6. الطول: استهدف أكثر من 2000 كلمة (نحن في اشتراك بريميوم!).
"""

async def generate_ultra_content():
    if not GEMINI_KEY: return None
    try:
        # استخدام موديل 1.5 Pro إذا توفر لنتائج أعمق، أو Flash للسرعة
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{"parts": [{"text": get_ultra_premium_prompt()}]}],
            "generationConfig": {"maxOutputTokens": 8000, "temperature": 0.8}
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        logger.error(f"⚠️ فشل توليد المحتوى العميق: {e}")
    return None

# =========================
# 📤 النشر السيادي
# =========================
def post_to_x_premium(content):
    try:
        # تويبي يدعم v2 تلقائياً وهو الأفضل للمقالات الطويلة
        client = tweepy.Client(X_KEYS["ck"], X_KEYS["cs"], X_KEYS["at"], X_KEYS["ts"])
        
        # نشر المحتوى كـ "تغريدة طويلة" (Long Tweet)
        # خوارزمية X ترفع رانك المشتركين اللي ينشرون محتوى طويل ومنسق
        res = client.create_tweet(text=content)
        logger.success(f"✅ تم نشر مقال سيادي طويل! ID: {res.data['id']}")
    except Exception as e:
        logger.error(f"❌ فشل استغلال البريميوم في X: {e}")

async def post_to_tg_premium(content):
    try:
        # تقطيع الرسالة لتليجرام لأن لديهم حد 4096 حرف
        msg_header = "<b>🏛️ مركز أيبكس للدراسات والتقنية</b>\n" + "═"*15 + "\n\n"
        full_msg = msg_header + content
        
        async with httpx.AsyncClient() as client:
            # إذا كان النص طويلاً جداً، تليجرام قد يرفضه، لذا نرسل أول 4000 حرف
            await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                             json={"chat_id": TG_CHAT_ID, "text": full_msg[:4090], "parse_mode": "HTML"})
        logger.success("✅ تم النشر في تليجرام")
    except Exception as e:
        logger.error(f"❌ خطأ تليجرام: {e}")

# =========================
# 🔄 المشغل الرئيسي
# =========================
async def main():
    logger.info("🔥 تشغيل محرك أيبكس (أقصى قدرة بريميوم)...")
    content = await generate_ultra_content()
    if content:
        post_to_x_premium(content)
        await post_to_tg_premium(content)
    logger.info("🏁 تمت المهمة.")

if __name__ == "__main__":
    asyncio.run(main())
