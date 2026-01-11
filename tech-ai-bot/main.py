import os
import logging
from dotenv import load_dotenv

# تحميل الإعدادات
load_dotenv()

# التأكد من وجود مجلد السجلات
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    try:
        logging.info("🤖 تشغيل البوت الموحّد: النشر التلقائي + الردود الذكية")

        # استيراد الوظائف محلياً لتجنب مشاكل المسارات
        from post_publisher import publish_tech_tweet
        from reply_agent import process_mentions

        # 1. مهمة النشر
        logging.info("--- بدء مهمة النشر ---")
        publish_tech_tweet()

        # 2. مهمة الردود
        bot_username = os.getenv("BOT_USERNAME")
        if bot_username:
            logging.info(f"--- معالجة الردود لـ @{bot_username} ---")
            process_mentions(bot_username)
        else:
            logging.warning("⚠️ BOT_USERNAME مفقود.")

        logging.info("✅ انتهت جميع العمليات بنجاح.")

    except Exception as e:
        logging.error(f"❌ خطأ في التشغيل الرئيسي: {e}")

if __name__ == "__main__":
    main()
