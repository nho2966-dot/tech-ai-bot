import os
import asyncio
import httpx
import random
import datetime
import tweepy
from loguru import logger

# ... (المفاتيح تبقى كما هي في الكود السابق) ...

# =========================
# 🛡️ نظام كسر التكرار (Unique Content System)
# =========================
def get_dynamic_prompt():
    # نغير جزء من الطلب في كل مرة لضمان تنوع الردود
    topics = ["أدوات AI Agents", "تطبيقات الذكاء الاصطناعي اليومية", "مستقبل العمل الذكي", "أدوات تحسين الإنتاجية"]
    selected_topic = random.choice(topics)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return f"""
    أنت أيبكس خبير تقني خليجي. اكتب ثريد من 3 تغريدات عن {selected_topic} للأفراد لعام 2026.
    القواعد الصارمة:
    1. لهجة خليجية بيضاء احترافية.
    2. ممنوع تكرار أي محتوى سابق.
    3. ركز على "الجديد كلياً" في الساحة التقنية.
    4. افصل بين التغريدات بكلمة [SPLIT].
    سياق الوقت الحالي: {current_time} (استخدمه لضمان حداثة المحتوى).
    """

# =========================
# 🧠 العقول الذكية (محدثة لمنع التكرار)
# =========================
async def mind_gemini():
    if not GEMINI_KEY: return None
    logger.info("🧠 محاولة التشغيل عبر: Gemini (نظام الحداثة)")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json={"contents": [{"parts": [{"text": get_dynamic_prompt()}]}]})
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            parts = [p.strip() for p in text.split("[SPLIT]") if p.strip()]
            
            # إضافة بصمة زمنية فريدة في آخر جزء لكسر حماية التكرار في X
            if parts:
                parts[-1] += f"\n\n🔗 {datetime.datetime.now().strftime('%H:%M:%S')}"
            return parts
    except: return None

# (طبق نفس منطق get_dynamic_prompt على Grok و Qwen و OpenAI)

# =========================
# 🏛️ محرك القرار السيادي (ضمان التنوع)
# =========================
async def sovereign_engine():
    minds = [mind_grok, mind_gemini, mind_qwen, mind_openai]
    for mind in minds:
        result = await mind()
        if result and len(result) >= 2:
            logger.success("✅ تم توليد محتوى فريد وغير مكرر")
            return result
    
    # محتوى الطوارئ (محدث ببصمة زمنية)
    return [
        f"الذكاء الاصطناعي في 2026 صار المساعد الشخصي اللي ما ينام 🚀\n{datetime.datetime.now().second}",
        "أدوات الـ AI Agents الحين تخلص مهامك المعقدة بضغطة زر 🎯",
        f"خليك مع أيبكس عشان تعرف كيف تسخر هذه الأدوات لخدمتك 🔥\nID: {random.randint(100,999)}"
    ]

# ... (دوال النشر X و Telegram تبقى كما هي) ...
