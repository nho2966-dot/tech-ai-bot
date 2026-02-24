import os
import asyncio
from loguru import logger
import tweepy
from openai import OpenAI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# ==========================================
# ⚙️ الإعدادات والمفاتيح
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", 0))

# ==========================================
# 🧠 محرك الذكاء الاصطناعي (تحليل الجمهور المتعدد)
# ==========================================
async def generate_insightful_reply(target_text):
    """
    يولد ردًا متوازنًا لكل طبقة جمهور: مبتدئ، متوسط، محترف
    ويضيف قيمة فعلية بناءً على التغريدة أو الخبر.
    """
    system_msg = """
أنت محلل تقني متمكن، تكتب محتوى عربي عملي وذو قيمة فعلية، 
يشرح الخبر أو المقارنة أو الأداة بطريقة تخدم:
1- المبتدئين: معلومة بسيطة ومباشرة
2- المتوسطين: تحليل عملي/تجريبي
3- المحترفين: insight معمق واستراتيجي
لا تقدم نصائح سطحية أو مجرد خبر.
ركز على المقارنات بين الأجهزة الذكية وأدوات الذكاء الاصطناعي والتقنيات العملية.
الرد يجب أن يكون كتغريدة واحدة (أقل من 280 حرف).
"""
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"اكتب ردًا على هذا النص:\n{target_text}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ في محرك الذكاء الاصطناعي: {e}")
        return None

# ==========================================
# 📱 إعداد غرفة عمليات تليجرام (القنص اليدوي الذكي)
# ==========================================
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

try:
    client_v2 = tweepy.Client(**X_CRED)
except Exception as e:
    logger.error(f"❌ خطأ في إعداد تويتر: {e}")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id != TELEGRAM_CHAT_ID:
        return
    await message.answer(
        "أهلاً بك في غرفة عمليات أيبكس 🎯\n"
        "لإرسال الردود العميقة استخدم:\n/reply [رقم_التغريدة] [نص التغريدة]"
    )

@dp.message(Command("reply"))
async def cmd_reply(message: Message):
    if message.from_user.id != TELEGRAM_CHAT_ID:
        await message.answer("⛔ غير مصرح لك باستخدام هذا البوت.")
        return

    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("⚠️ صياغة خاطئة! الصيغة الصحيحة:\n/reply 1892837482 نص التغريدة")
        return

    tweet_id = parts[1]
    target_text = parts[2]

    if not tweet_id.isdigit():
        await message.answer("⚠️ رقم التغريدة يجب أن يحتوي على أرقام فقط!")
        return

    status_msg = await message.answer("⏳ جاري تحليل التغريدة وصياغة الرد المعمق...")

    # توليد الرد
    reply_content = await generate_insightful_reply(target_text)
    if not reply_content:
        await status_msg.edit_text("❌ فشل الذكاء الاصطناعي في صياغة الرد.")
        return

    # نشر الرد على تويتر
    try:
        client_v2.create_tweet(text=reply_content, in_reply_to_tweet_id=tweet_id)
        await status_msg.edit_text(f"✅ تم نشر الرد بنجاح!\n\n📝 الرد المنشور:\n{reply_content}")
        logger.success(f"تم الرد على {tweet_id} بنجاح.")
    except tweepy.errors.TweepyException as e:
        await status_msg.edit_text(f"❌ خطأ أثناء النشر على تويتر:\n{e}")
        logger.error(f"فشل النشر: {e}")

# ==========================================
# 🚀 تشغيل النظام
# ==========================================
async def main():
    logger.info("🚀 تشغيل غرفة عمليات تليجرام للقنص...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
