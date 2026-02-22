import os
import asyncio
import httpx
import random
import datetime
import tweepy
from loguru import logger

# =========================
# 🔐 ربط المفاتيح (حسب مسمياتك)
# =========================
XAI_KEY = os.getenv("XAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
QWEN_KEY = os.getenv("QWEN_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

TG_TOKEN = os.getenv("TG_TOKEN")
# معالجة ذكية للـ Chat ID لضمان قبول تليجرام له كقناة
RAW_TG_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_CHAT_ID = RAW_TG_ID if RAW_TG_ID.startswith("-100") else f"-100{RAW_TG_ID}"

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# =========================
# 🛡️ المحرك الذكي (مكافحة التكرار والتقادم)
# =========================
def get_strictly_fresh_prompt():
    topics = [
        "أحدث أدوات AI Agents الشخصية لعام 2026",
        "كيفية أتمتة المهام اليومية للأفراد باستخدام الذكاء الاصطناعي",
        "أدوات الذكاء الاصطناعي التي أحدثت ثورة في الإنتاجية الشخصية",
        "مستقبل الهواتف الذكية مع Artificial Intelligence and its latest tools"
    ]
    current_moment = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return f"""
    بصفتك 'أيبكس' الخبير التقني، اكتب ثريد خليجي أبيض من 3 تغريدات عن: {random.choice(topics)}.
    النظام الصارم:
    1. ابدأ بمحتوى طازج وحصري لعام 2026.
    2. استخدم أسلوباً احترافياً بعيداً عن التكرار الممل.
    3. افصل بـ [SPLIT].
    4. السياق الزمني الحالي: {current_moment} (استخدمه لمنع توليد محتوى قديم).
    """

async def generate_content():
    minds = [
        ("Grok", "https://api.x.ai/v1/chat/completions", XAI_KEY),
        ("Gemini", f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}", GEMINI_KEY)
    ]
    
    for name, url, key in minds:
        if not key: continue
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                logger.info(f"🧠 استدعاء عقل: {name}")
                if name == "Grok":
                    r = await client.post(url, headers={"Authorization": f"Bearer {key}"}, 
                        json={"model": "grok-2-latest", "messages": [{"role": "user", "content": get_strictly_fresh_prompt()}]})
                    text = r.json()["choices"][0]["message"]["content"]
                else:
                    r = await client.post(url, json={"contents": [{"parts": [{"text": get_strictly_fresh_prompt()}]}]})
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                
                parts = [p.strip() for p in text.split("[SPLIT]") if p.strip()]
                if len(parts) >= 2:
                    # إضافة بصمة فريدة (Unique Hash) لمنع رفض X للمحتوى المتشابه
                    unique_id = hex(random.getrandbits(16))[2:]
                    parts[-1] += f"\n\n🔖 {unique_id}"
                    return parts
        except Exception as e:
            logger.error(f"⚠️ تعثر {name}: {e}")
    
    # محتوى الطوارئ بنظام البصمة
    return [f"الـ AI في 2026 صار رفيقك الدائم 🚀\n{datetime.datetime.now().second}", "أدواتك صارت أذكى بضغطة زر 🎯", f"أيبكس يواكب لك كل جديد 🔥\nRef: {random.randint(100,999)}"]

# =========================
# 🚀 محرك النشر السيادي
# =========================
def post_to_x(content):
    try:
        client = tweepy.Client(X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S)
        last_id = None
        for part in content:
            res = client.create_tweet(text=part[:280], in_reply_to_tweet_id=last_id)
            last_id = res.data["id"]
        logger.success("✅ تم النشر في X")
    except Exception as e: logger.error(f"❌ خطأ X: {e}")

async def post_to_tg(content):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": "🧵 <b>ثريد أيبكس التقني</b>\n\n" + "\n\n".join(content),
            "parse_mode": "HTML"
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200: logger.success("✅ تم النشر في تليجرام")
            else: logger.error(f"❌ تليجرام رفض: {r.text}")
    except Exception as e: logger.error(f"❌ عطل تليجرام: {e}")

async def main():
    content = await generate_content()
    post_to_x(content)
    await post_to_tg(content)

if __name__ == "__main__":
    asyncio.run(main())
