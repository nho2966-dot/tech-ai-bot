import os
import logging
from dotenv import load_dotenv

# تحميل المتغيرات (للاستخدام المحلي)
load_dotenv()

# إعداد التسجيل الموحّد
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    """الوظيفة الرئيسية: نشر تلقائي + ردود ذكية"""
    try:
        logging.info("🤖 تشغيل البوت الموحّد...")

        # استيراد المهام بعد التحديثات
        from post_publisher import publish_tech_tweet
        from reply_agent import process_mentions

        # 1. نشر تغريدة تقنية
        publish_tech_tweet()

        # 2. الرد على التغريدات الموجهة
        bot_username = os.getenv("BOT_USERNAME")
        if bot_username:
            process_mentions(bot_username)
        else:
            logging.warning("⚠️ BOT_USERNAME غير مضبوط — لن يتم الرد على التغريدات.")

        logging.info("✅ اكتملت جميع المهام بنجاح.")

    except Exception as e:
        logging.error(f"❌ فشل تشغيل البوت: {e}")
        raise

if __name__ == "__main__":
    main()
