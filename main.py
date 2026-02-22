import os, asyncio, httpx, random, datetime, tweepy
from loguru import logger

# =========================
# 🔐 ربط المفاتيح (المسميات المتفق عليها)
# =========================
GEMINI_KEY = os.getenv("GEMINI_KEY")
XAI_KEY = os.getenv("XAI_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
QWEN_KEY = os.getenv("QWEN_API_KEY")

TG_TOKEN = os.getenv("TG_TOKEN")
# تأمين صيغة ID القناة بشكل برمجي صارم
RAW_TG_ID = os.getenv("TELEGRAM_CHAT_ID", "").replace(" ", "")
if RAW_TG_ID and not RAW_TG_ID.startswith("-100") and not RAW_TG_ID.startswith("@"):
    TG_CHAT_ID = f"-100{RAW_TG_ID}"
else:
    TG_CHAT_ID = RAW_TG_ID

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# =========================
# 🛡️ نظام منع التكرار والتقادم
# =========================
def get_strictly_fresh_prompt():
    topics = [
        "أدوات AI Agents الشخصية لعام 2026",
        "كيفية أتمتة المهام اليومية باستخدام Artificial Intelligence and its latest tools",
        "أدوات ذكاء اصطناعي ثورية للأفراد في دول الخليج",
        "مستقبل الإنتاجية الشخصية مع المساعدين الأذكياء"
    ]
    # البصمة الزمنية لمنع التكرار في عقول الـ AI
    current_moment = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
بصفتك 'أيبكس' الخبير التقني الخليجي، اكتب ثريد من 3 تغريدات عن: {random.choice(topics)}.
النظام الصارم:
1. المحتوى طازج وحصري لعام 2026.
2. اللهجة: خليجية بيضاء احترافية.
3. افصل بين التغريدات بكلمة [SPLIT].
4. بصمة الوقت الحالية: {current_moment}.
"""

# =========================
# 🌐 محرك التوليد (Fallback System)
# =========================
async def generate_content():
    minds = [
        ("Gemini", f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"),
        ("Grok", "https://api.x.ai/v1/chat/completions")
    ]
    
    for name, url in minds:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                logger.info(f"🧠 استدعاء عقل: {name}")
                if name == "Gemini" and GEMINI_KEY:
                    # تجاوز فلاتر الحماية لضمان الاستجابة
                    payload = {
                        "contents": [{"parts": [{"text": get_strictly_fresh_prompt()}]}],
                        "safetySettings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
                    }
                    r = await client.post(url, json=payload)
                    data = r.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                elif name == "Grok" and XAI_KEY:
                    r = await client.post(url, headers={"Authorization": f"Bearer {XAI_KEY}"}, 
                        json={"model": "grok-2-latest", "messages": [{"role": "user", "content": get_strictly_fresh_prompt()}]})
                    text = r.json()["choices"][0]["message"]["content"]
                else: continue

                parts = [p.strip() for p in text.split("[SPLIT]") if p.strip()]
                if len(parts) >= 2:
                    # إضافة بصمة (Unique Fingerprint) لكسر حظر التكرار في X
                    unique_mark = f"\n\n🔖 {hex(random.getrandbits(16))[2:]}"
                    parts[-1] += unique_mark
                    return parts
        except Exception as e:
            logger.warning(f"⚠️ تعثر {name}: {e}")
            continue

    return [f"الذكاء الاصطناعي في 2026 صار رفيقك الدائم 🚀\n{datetime.datetime.now().second}", "أدواتك صارت أذكى بضغطة زر 🎯", f"أيبكس يواكب لك كل جديد 🔥\nRef: {random.randint(100,999)}"]

# =========================
# 🚀 محرك النشر السيادي (X & Telegram)
# =========================
def post_to_x(content):
    if not all([X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S]):
        logger.error("❌ مفاتيح X ناقصة")
        return
    try:
        client = tweepy.Client(X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S)
        last_id = None
        for part in content:
            res = client.create_tweet(text=part[:280], in_reply_to_tweet_id=last_id)
            last_id = res.data["id"]
        logger.success("✅ تم النشر في X بنجاح")
    except Exception as e: logger.error(f"❌ خطأ X: {e}")

async def post_to_tg(content):
    if not TG_TOKEN or not TG_CHAT_ID:
        logger.error("❌ معلومات تليجرام ناقصة")
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        full_text = "🧵 <b>ثريد أيبكس التقني</b>\n\n" + "\n\n".join(content)
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json={"chat_id": TG_CHAT_ID, "text": full_text, "parse_mode": "HTML"})
            if r.status_code == 200: logger.success("✅ تم النشر في تليجرام")
            else: logger.error(f"❌ تليجرام رفض: {r.text}")
    except Exception as e: logger.error(f"❌ عطل تليجرام: {e}")

# =========================
# 🔄 التشغيل
# =========================
async def main():
    logger.info("🚀 انطلاق محرك أيبكس...")
    content = await generate_content()
    post_to_x(content)
    await post_to_tg(content)

if __name__ == "__main__":
    asyncio.run(main())
