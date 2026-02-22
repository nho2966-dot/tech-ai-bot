import os
import asyncio
import httpx
import random
import tweepy
from loguru import logger

# =========================
# 🔐 ربط المفاتيح (بناءً على صورك)
# =========================
XAI_KEY = os.getenv("XAI_API_KEY")       # مطابق لصورتك
GEMINI_KEY = os.getenv("GEMINI_KEY")     # مطابق لصورتك
OPENAI_KEY = os.getenv("OPENAI_API_KEY") # مطابق لصورتك
QWEN_KEY = os.getenv("QWEN_API_KEY")     # مطابق لصورتك (تأكد من السبيلنج)

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# =========================
# 🧠 العقل الأول - Grok (Grok is your XAI_API_KEY)
# =========================
async def mind_grok():
    if not XAI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Grok (XAI)")
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "grok-2-latest",
        "messages": [{"role": "user", "content": "أنت أيبكس خبير تقني خليجي. اكتب ثريد من 3 تغريدات عن أدوات AI للأفراد 2026 بلهجة خليجية بيضاء. افصل بـ [SPLIT]"}]
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            text = r.json()["choices"][0]["message"]["content"]
            return [p.strip() for p in text.split("[SPLIT]") if p.strip()]
    except Exception as e:
        logger.error(f"Grok Error: {e}")
        return None

# (بقية العقول Gemini و OpenAI تبقى كما هي مع التأكد من مسميات الـ Env)

# =========================
# 🏛️ محرك القرار السيادي (المطابق للصور)
# =========================
async def sovereign_engine():
    # الترتيب حسب رغبتك (Grok أولاً)
    minds = [mind_grok, mind_gemini, mind_openai]
    for mind in minds:
        result = await mind()
        if result and len(result) >= 2:
            return result
    
    # محتوى احتياطي مطور عشان ما يتكرر القديم
    return [
        "الذكاء الاصطناعي في 2026 صار المساعد الشخصي اللي ما ينام 🚀",
        "أدوات الـ AI Agents الحين تخلص مهامك المعقدة بضغطة زر 🎯",
        "خليك مع أيبكس عشان تعرف كيف تسخر هذه الأدوات لخدمتك 🔥"
    ]

# (تكملة دالة النشر في X و Telegram)
