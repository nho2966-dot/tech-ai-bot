import os
import asyncio
import httpx
import tweepy
from google import genai
from openai import OpenAI
from loguru import logger

# --- إعدادات الوصول والأمان ---
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "XAI": os.getenv("XAI_API_KEY"),
    "OPENROUTER": os.getenv("OPENROUTER_API_KEY"),
    "QWEN": os.getenv("QWEN_API_KEY"),
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- برومبت "أيبكس" السيادي المطور (الخبايا والسبق الصحفي) ---
SYSTEM_PROMPT = """
أنت 'أيبكس' (Apex)، الخبير التقني الأول في الخليج لعام 2026. 
مهمتك: تقديم سبق صحفي (Scoop) وخبايا تقنية لا يعرفها العامة.

المتطلبات:
1. التركيز: خبايا الذكاء الاصطناعي، أسرار الأجهزة الذكية (S26 Ultra, iPhone 17, Meta Glasses)، وكيفية استغلالها لزيادة الدخل والإنتاجية.
2. الأسلوب: لغة خليجية بيضاء، فخمة، احترافية جداً، ومختصرة.
3. التنسيق: 
   - يبدأ بعبارة [سبق صحفي] أو [خبايا تقنية].
   - استخدام النقاط والرموز التعبيرية (Emojis) بشكل ذكي.
   - ذكر المصطلحات الإنجليزية التقنية بين قوسين.
4. الجودة: لا تقبل المعلومات السطحية، ابحث عن 'الثغرات' الإيجابية والميزات المخفية (Hidden Features).
"""

# --- المحركات الستة المتتابعة ---
async def brain_gemini():
    client = genai.Client(api_key=KEYS["GEMINI"])
    res = client.models.generate_content(model="gemini-2.0-flash", contents=SYSTEM_PROMPT)
    return res.text

async def brain_openai():
    client = OpenAI(api_key=KEYS["OPENAI"])
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def brain_groq():
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def brain_xai():
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=KEYS["XAI"])
    res = client.chat.completions.create(model="grok-2-latest", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def brain_openrouter():
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=KEYS["OPENROUTER"])
    res = client.chat.completions.create(model="anthropic/claude-3.5-sonnet", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def brain_qwen():
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=KEYS["QWEN"])
    res = client.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def get_content():
    brains = [
        ("Gemini", brain_gemini), ("OpenAI", brain_openai), ("Groq", brain_groq),
        ("xAI (Grok)", brain_xai), ("OpenRouter", brain_openrouter), ("Qwen", brain_qwen)
    ]
    for name, func in brains:
        try:
            logger.info(f"🔄 جاري استخراج سبق صحفي عبر: {name}")
            content = await func()
            if content: return content
        except Exception as e:
            logger.warning(f"⚠️ {name} تعذر الوصول إليه.")
    return None

# --- قنوات النشر المحدثة ---
def post_to_x(content):
    try:
        # الربط مع API v2 للنشر الاحترافي
        client = tweepy.Client(
            consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
            access_token=X_CRED["at"], access_token_secret=X_CRED["ts"]
        )
        client.create_tweet(text=content[:24500]) # دعم مساحة البريميوم الكاملة
        logger.success("✅ تم النشر بنجاح على X")
    except Exception as e:
        logger.error(f"❌ خطأ في X: {e}")

async def post_to_telegram(content):
    if not TG_TOKEN: return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={
                "chat_id": TG_CHAT_ID, "text": f"🚀 *أيبكس | سبق صحفي*\n\n{content[:4000]}", "parse_mode": "Markdown"
            })
        logger.success("✅ تم الإرسال لتليجرام")
    except Exception as e:
        logger.error(f"❌ خطأ تليجرام: {e}")

# --- المشغل الرئيسي ---
async def main():
    logger.info("🔥 تشغيل محرك ناصر السيادي لعام 2026...")
    content = await get_content()
    if content:
        post_to_x(content)
        await post_to_telegram(content)
    else:
        logger.critical("🚨 فشل في الوصول لأي عقل تقني!")

if __name__ == "__main__":
    asyncio.run(main())
