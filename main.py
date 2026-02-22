import os
import asyncio
import httpx
import random
import tweepy
from loguru import logger

# =========================
# 🔐 ربط المفاتيح (مطابق لصورك 100%)
# =========================
XAI_KEY = os.getenv("XAI_API_KEY")       # عقل Grok (الخيار الأول)
GEMINI_KEY = os.getenv("GEMINI_KEY")     # عقل Gemini (الخيار الثاني)
QWEN_KEY = os.getenv("QWEN_API_KEY")     # عقل Qwen (الخيار الثالث)
OPENAI_KEY = os.getenv("OPENAI_API_KEY") # عقل OpenAI (الخيار الرابع)

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# =========================
# 🧠 العقل الأول (جوك) - Grok
# =========================
async def mind_grok():
    if not XAI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Grok (XAI)")
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
    except: return None

# =========================
# 🧠 العقل الثاني - Gemini
# =========================
async def mind_gemini():
    if not GEMINI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Gemini")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json={"contents": [{"parts": [{"text": "اكتب ثريد تقني خليجي من 3 اجزاء عن ادوات AI 2026 للأفراد بلهجة بيضاء. افصل بـ [SPLIT]"}]}]})
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except: return None

# =========================
# 🧠 العقل الثالث - Qwen (عبر OpenRouter)
# =========================
async def mind_qwen():
    if not QWEN_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Qwen (العقل الثالث)")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {QWEN_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [{"role": "user", "content": "ثريد تقني خليجي من 3 تغريدات عن أدوات AI للأفراد 2026. افصل بـ [SPLIT]"}]
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(url, headers=headers, json=payload)
            text = r.json()["choices"][0]["message"]["content"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except: return None

# =========================
# 🧠 العقل الرابع - OpenAI
# =========================
async def mind_openai():
    if not OPENAI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: OpenAI")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", 
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "ثريد تقني خليجي 3 تغريدات عن AI 2026. افصل بـ [SPLIT]"}]})
            text = r.json()["choices"][0]["message"]["content"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except: return None

# =========================
# 🏛️ محرك القرار السيادي
# =========================
async def sovereign_engine():
    minds = [mind_grok, mind_gemini, mind_qwen, mind_openai]
    for mind in minds:
        result = await mind()
        if result and len(result) >= 2:
            logger.success("✅ تم استدعاء المحتوى بنجاح من العقول الذكية")
            return result
    
    # محتوى الطوارئ (Fallback)
    return [
        "الذكاء الاصطناعي في 2026 صار المساعد الشخصي اللي ما ينام 🚀",
        "أدوات الـ AI Agents الحين تخلص مهامك المعقدة بضغطة زر 🎯",
        "خليك مع أيبكس عشان تعرف كيف تسخر هذه الأدوات لخدمتك 🔥"
    ]

# =========================
# 🚀 تنفيذ النشر (X & Telegram)
# =========================
def post_to_x(content):
    try:
        client = tweepy.Client(consumer_key=X_KEY, consumer_secret=X_SECRET, access_token=X_TOKEN, access_token_secret=X_ACCESS_S)
        last_id = None
        for part in content:
            res = client.create_tweet(text=part[:280], in_reply_to_tweet_id=last_id)
            last_id = res.data["id"]
        logger.success("✅ تم النشر في X بنجاح")
    except Exception as e: logger.error(f"❌ خطأ X: {e}")

async def post_to_tg(content):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        text = "🧵 <b>ثريد أيبكس التقني</b>\n\n" + "\n\n".join(content)
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"})
        logger.success("✅ تم النشر في Telegram بنجاح")
    except Exception as e: logger.error(f"❌ خطأ تليجرام: {e}")

async def main():
    logger.info("🚀 انطلاق محرك أيبكس الرباعي...")
    content = await sovereign_engine()
    
    # النشر بنظام الفصل السيادي (كل منصة مستقلة)
    post_to_x(content)
    await post_to_tg(content)
    
    logger.info("🏁 انتهت المهمة بنجاح")

if __name__ == "__main__":
    asyncio.run(main())
