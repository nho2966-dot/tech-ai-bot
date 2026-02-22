import os
import asyncio
import httpx
import random
import tweepy
from loguru import logger

# =========================
# 🔐 ربط المفاتيح (مطابق لصورك يا ناصر)
# =========================
XAI_KEY = os.getenv("XAI_API_KEY")       # عقل Grok
GEMINI_KEY = os.getenv("GEMINI_KEY")     # عقل Gemini
OPENAI_KEY = os.getenv("OPENAI_API_KEY") # عقل OpenAI
QWEN_KEY = os.getenv("QWEN_API_KEY")     # عقل Qwen (الاحتياطي)

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# =========================
# 🧵 محتوى الطوارئ (في حال صمتت العقول)
# =========================
FALLBACK_THREADS = [
    [
        "الذكاء الاصطناعي في 2026 صار المساعد الشخصي اللي ما ينام 🚀",
        "أدوات الـ AI Agents الحين تخلص مهامك المعقدة بضغطة زر 🎯",
        "خليك مع أيبكس عشان تعرف كيف تسخر هذه الأدوات لخدمتك 🔥"
    ],
    [
        "Artificial Intelligence and its latest tools غيرت قواعد اللعبة للأفراد 🧠",
        "الإنتاجية تضاعفت بفضل الأدوات الذكية اللي تنفذ بدالنا المهام الروتينية 👨🏻‍💻",
        "المستقبل موجود الآن، خلك مستعد مع أيبكس ⚡"
    ]
]

# =========================
# 🧠 العقل الأول (جوك) - Grok
# =========================
async def mind_grok():
    if not XAI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Grok (الخيار الأول)")
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "grok-2-latest",
        "messages": [{"role": "user", "content": "أنت أيبكس خبير تقني خليجي. اكتب ثريد من 3 تغريدات عن أدوات AI للأفراد 2026 بلهجة خليجية بيضاء. افصل بين كل تغريدة بكلمة [SPLIT]"}]
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(url, headers=headers, json=payload)
            text = r.json()["choices"][0]["message"]["content"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except Exception as e:
        logger.error(f"❌ Grok واجه عائق: {e}")
        return None

# =========================
# 🧠 العقل الثاني - Gemini
# =========================
async def mind_gemini():
    if not GEMINI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Gemini")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json={"contents": [{"parts": [{"text": "اكتب ثريد تقني خليجي من 3 اجزاء عن ادوات AI 2026. افصل بـ [SPLIT]"}]}]})
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except: return None

# =========================
# 🧠 العقل الثالث - OpenAI
# =========================
async def mind_openai():
    if not OPENAI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: OpenAI")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", 
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "ثريد تقني خليجي 3 تغريدات عن AI 2026 للأفراد. افصل بـ [SPLIT]"}]})
            text = r.json()["choices"][0]["message"]["content"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except: return None

# =========================
# 🏛️ محرك القرار السيادي
# =========================
async def sovereign_engine():
    minds = [mind_grok, mind_gemini, mind_openai]
    for mind in minds:
        result = await mind()
        if result and len(result) >= 2:
            logger.success("✅ تم استدعاء المحتوى بنجاح من العقول")
            return result
    logger.warning("⚠️ جميع العقول فشلت - تفعيل محتوى الطوارئ")
    return random.choice(FALLBACK_THREADS)

# =========================
# 🚀 تنفيذ النشر في X
# =========================
def post_to_x(content):
    try:
        client = tweepy.Client(consumer_key=X_KEY, consumer_secret=X_SECRET, access_token=X_TOKEN, access_token_secret=X_ACCESS_S)
        last_id = None
        for part in content:
            res = client.create_tweet(text=part[:280], in_reply_to_tweet_id=last_id)
            last_id = res.data["id"]
        logger.success("✅ تم النشر في X بنجاح")
    except Exception as e:
        logger.error(f"❌ فشل النشر في X: {e}")

# =========================
# 🚀 تنفيذ النشر في Telegram
# =========================
async def post_to_tg(content):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        text = "🧵 <b>ثريد أيبكس التقني</b>\n\n" + "\n\n".join(content)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"})
            if r.status_code != 200:
                logger.error(f"⚠️ تليجرام رفض الإرسال: {r.text}")
            else:
                logger.success("✅ تم النشر في Telegram بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ تليجرام: {e}")

# =========================
# 🏁 المحرك الرئيسي (الفصل السيادي)
# =========================
async def main():
    logger.info("🚀 انطلاق محرك أيبكس المطور...")
    
    # 1. توليد المحتوى
    content = await sovereign_engine()
    
    # 2. النشر في X (مستقل)
    post_to_x(content)
    
    # 3. النشر في تليجرام (مستقل)
    await post_to_tg(content)
    
    logger.info("🏁 انتهت الجولة التقنية")

if __name__ == "__main__":
    asyncio.run(main())
