import os
import asyncio
import httpx
import tweepy
from google import genai
from openai import OpenAI
from loguru import logger

# ==========================================
# 🔐 إدارة الهوية (Secrets)
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "XAI": os.getenv("XAI_API_KEY"),
    "OPENROUTER": os.getenv("OPENROUTER_API_KEY"),
    "QWEN": os.getenv("QWEN_API_KEY"),
}

# إعدادات X وتليجرام
X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================
# 🧠 البرومبت الملكي (الخبايا والسبق الصحفي)
# ==========================================
SYSTEM_PROMPT = """
أنت 'أيبكس' (Apex)، الخبير التقني والصحفي الاستقصائي الأول في الخليج لعام 2026.
مهمتك: تقديم سبق صحفي (Scoop) وخبايا تقنية احترافية جداً للأفراد.

القواعد الصارمة:
1. اللغة: استخدم اللغة العربية (لهجة خليجية بيضاء فخمة) فقط. يمنع منعاً باتاً استخدام اليابانية أو الصينية أو أي لغات أخرى.
2. المحتوى: ابحث عن أسرار (Hidden Features) في (S26 Ultra, iPhone 17, Meta Glasses) والذكاء الاصطناعي التي تزيد الدخل والإنتاجية.
3. الصياغة: ابدأ بـ [سبق صحفي] أو [خبايا تقنية]. كن مهنياً، محفزاً، ومختصراً.
4. التنسيق: ضع المصطلحات التقنية الإنجليزية بين قوسين فقط. استخدم الإيموجي بذكاء.
5. الجودة: يمنع تكرار الجمل أو كتابة معلومات بديهية. نبي "أسرار" حقيقية.
"""

# ==========================================
# 📡 محركات التوليد (نظام الصمود الستة)
# ==========================================

async def fetch_gemini():
    client = genai.Client(api_key=KEYS["GEMINI"])
    res = client.models.generate_content(model="gemini-2.0-flash", contents=SYSTEM_PROMPT)
    return res.text

async def fetch_openai():
    client = OpenAI(api_key=KEYS["OPENAI"])
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def fetch_groq():
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def fetch_xai():
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=KEYS["XAI"])
    res = client.chat.completions.create(model="grok-2-latest", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def fetch_openrouter():
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=KEYS["OPENROUTER"])
    res = client.chat.completions.create(model="anthropic/claude-3.5-sonnet", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def fetch_qwen():
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=KEYS["QWEN"])
    res = client.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "user", "content": SYSTEM_PROMPT}])
    return res.choices[0].message.content

async def get_sovereign_content():
    brains = [
        ("Gemini", fetch_gemini), ("OpenAI", fetch_openai), ("Groq", fetch_groq),
        ("xAI (Grok)", fetch_xai), ("OpenRouter", fetch_openrouter), ("Qwen", fetch_qwen)
    ]
    for name, brain_func in brains:
        try:
            logger.info(f"🔄 محاولة استخراج سبق صحفي عبر عقل: {name}")
            content = await brain_func()
            if content and len(content) > 100:
                logger.success(f"⭐ تم النجاح بواسطة {name}")
                return content
        except Exception as e:
            logger.warning(f"⚠️ عقل {name} لم يستجب: {e}")
    return None

# ==========================================
# 📤 قنوات النشر (X & Telegram)
# ==========================================

def post_to_x(content):
    try:
        client = tweepy.Client(
            consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
            access_token=X_CRED["at"], access_token_secret=X_CRED["ts"]
        )
        # النشر للحسابات المدفوعة (دعم التغريدات الطويلة)
        client.create_tweet(text=content[:24500])
        logger.success("✅ تم اجتياح منصة X بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في X: {e}")

async def post_to_tg(content):
    if not TG_TOKEN: return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={
                "chat_id": TG_CHAT_ID, "text": f"🚀 *أيبكس | حصري*\n\n{content[:4000]}", "parse_mode": "Markdown"
            })
        logger.success("✅ تم الإرسال لتليجرام")
    except Exception as e:
        logger.error(f"❌ خطأ تليجرام: {e}")

# ==========================================
# 🏁 المشغل الرئيسي
# ==========================================

async def main():
    logger.info("🔥 تشغيل محرك ناصر السيادي (أيبكس 2026)...")
    content = await get_sovereign_content()
    if content:
        post_to_x(content)
        await post_to_tg(content)
    else:
        logger.critical("🚨 جميع العقول الستة تعطلت! راجع الكوتا والمفاتيح.")

if __name__ == "__main__":
    asyncio.run(main())
