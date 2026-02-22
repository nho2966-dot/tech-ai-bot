import os
import asyncio
import logging
from datetime import datetime
import openai
import google.generativeai as genai
from loguru import logger
from dotenv import load_dotenv

# ======== إعداد البيئة ========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GEMINI_KEY)

# ======== إعداد Logger ========
logger.add("bot_log.log", rotation="5 MB", level="INFO")

# ======== دوال الاتصال بالنماذج ========
async def call_gemini_model(model_name: str, prompt: str):
    """توليد محتوى باستخدام Gemini"""
    try:
        response = genai.generate_text(model=model_name, prompt=prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gemini Error: {e}")

async def call_openai_model(model_name: str, prompt: str):
    """توليد محتوى باستخدام OpenAI"""
    try:
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"OpenAI Error: {e}")

async def get_available_gemini_models():
    """إرجاع قائمة نماذج Gemini المتاحة"""
    try:
        models = genai.list_models()
        return [m.name for m in models if "gemini" in m.name.lower()]
    except Exception as e:
        logger.warning(f"⚠️ خطأ في جلب نماذج Gemini: {e}")
        return []

# ======== دالة التوليد الذكية ========
async def generate_ultra_content(prompt: str, retries: int = 3):
    """توليد المحتوى مع fallback ديناميكي"""
    gemini_models = await get_available_gemini_models()
    fallback_models = ["gpt-4.1", "gpt-3.5-turbo"]

    for attempt in range(1, retries + 1):
        logger.info(f"🛠️ محاولة توليد المحتوى رقم {attempt}")
        # تجربة نماذج Gemini أولاً
        for model_name in gemini_models:
            try:
                content = await call_gemini_model(model_name, prompt)
                logger.info(f"✅ تم التوليد بنجاح بواسطة {model_name}")
                return content
            except Exception as e:
                logger.error(f"❌ خطأ Gemini {model_name}: {e}")

        # إذا فشل كل Gemini ننتقل إلى OpenAI
        for model_name in fallback_models:
            try:
                content = await call_openai_model(model_name, prompt)
                logger.info(f"✅ تم التوليد بنجاح بواسطة {model_name}")
                return content
            except Exception as e:
                logger.error(f"❌ خطأ OpenAI {model_name}: {e}")

        await asyncio.sleep(2)  # تأخير قبل المحاولة التالية

    logger.error("❌ فشل كل النماذج بعد المحاولات المتعددة")
    return None

# ======== الوظيفة الرئيسية ========
async def main():
    logger.info("🔥 تشغيل محرك Apex الذكي")
    prompt = "اكتب محتوى تقني متنوع جاهز للنشر على تويتر وTelegram"
    content = await generate_ultra_content(prompt)

    if content:
        logger.info(f"📝 المحتوى النهائي:\n{content}")
        # هنا يمكن إضافة نشر المحتوى على X أو Telegram
    else:
        logger.warning("⚠️ لم يتم توليد أي محتوى للنشر")

    logger.info("🏁 تمت المهمة.")

# ======== تشغيل البوت ========
if __name__ == "__main__":
    asyncio.run(main())
