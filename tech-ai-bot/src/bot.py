import os
import logging
from dotenv import load_dotenv

# تحميل المتغيرات من .env (اختياري، لكن مفيد للتشغيل المحلي)
load_dotenv()

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    """
    الملف الرئيسي لتشغيل البوت كوحدة واحدة:
    - نشر التغريدات التلقائية
    - الرد على التغريدات الموجهة
    """
    try:
        # استيراد الملفات بعد تهيئة التسجيل
        from post_publisher import publish_tech_tweet
        from reply_agent import process_mentions

        logging.info("🚀 بدء تشغيل البوت الموحّد...")

        # 1. نشر التغريدة التلقائية
        logging.info("🔍 تشغيل مهمة النشر...")
        publish_tech_tweet()

        # 2. معالجة الردود على التغريدات
        logging.info("💬 تشغيل مهمة الردود...")
        bot_username = os.getenv("BOT_USERNAME", "TechAI_Bot")
        process_mentions(bot_username)

        logging.info("✅ اكتملت جميع المهام بنجاح!")

    except ImportError as e:
        logging.error(f"❌ خطأ في الاستيراد: {e}")
    except Exception as e:
        logging.error(f"❌ خطأ غير متوقع: {e}")

if __name__ == "__main__":
    main()
