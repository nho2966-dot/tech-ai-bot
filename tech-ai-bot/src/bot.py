@@ -1,45 +1,49 @@
import os
import logging
from dotenv import load_dotenv

# تحميل المتغيرات (اختياري — مفيد في التطوير المحلي)
load_dotenv()

# إعداد نظام التسجيل الموحّد
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    """الوظيفة الرئيسية: تشغيل المهام: النشر + الردود."""
    try:
        logging.info("🤖 تشغيل البوت الموحّد: النشر التلقائي + الردود الذكية")

        # استيراد الوظائف بعد التحديثات
        from post_publisher import publish_tech_tweet
        from reply_agent import process_mentions

        # 1. نشر تغريدة تقنية
        publish_tech_tweet()

        # 2. الرد على التغريدات الموجهة
        bot_username = os.getenv("BOT_USERNAME")
        if bot_username:
            logging.info(f"البدء في معالجة الردود على @{bot_username}")
            process_mentions(bot_username)
        else:
            logging.warning("⚠️ BOT_USERNAME غير مضبوط — لن يتم معالجة الردود.")

        logging.info("✅ اكتملت جميع المهام بنجاح.")

    except Exception as e:
        logging.error(f"❌ فشل تشغيل البوت الموحّد: {e}")
        raise

if __name__ == "__main__":
    main()
