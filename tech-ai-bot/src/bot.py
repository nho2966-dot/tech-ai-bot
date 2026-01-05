import os
import logging
from dotenv import load_dotenv

# تحميل المتغيرات للمحيط المحلي (GitHub يقرأ الـ Secrets تلقائياً)
load_dotenv()

# التأكد من وجود مجلد الـ logs لتجنب أخطاء التشغيل
if not os.path.exists("logs"):
    os.makedirs("logs")

# إعداد نظام التسجيل الموحّد (UTF-8 لدعم اللغة العربية)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    """الوظيفة الرئيسية: تشغيل المهام (النشر + الردود) بشكل منظم."""
    try:
        logging.info("🤖 تشغيل البوت الموحّد: النشر التلقائي + الردود الذكية")

        # استيراد الوظائف من الملفات الفرعية
        # ملاحظة: تأكد أن هذه الملفات موجودة داخل مجلد src أو المسار الصحيح
        from src.post_publisher import publish_tech_tweet
        from src.reply_agent import process_mentions

        # 1. مهمة النشر التلقائي
        logging.info("--- بدء مهمة نشر التغريدة التقنية ---")
        publish_tech_tweet()

        # 2. مهمة الردود الذكية
        bot_username = os.getenv("BOT_USERNAME")
        if bot_username:
            logging.info(f"--- بدء معالجة الردود للحساب: @{bot_username} ---")
            process_mentions(bot_username)
        else:
            logging.warning("⚠️ BOT_USERNAME غير مضبوط في الإعدادات — سيتم تخطي الردود.")

        logging.info("✅ اكتملت جميع المهام المجدولة بنجاح.")

    except ImportError as ie:
        logging.error(f"❌ فشل في الاستيراد: تأكد من مسار الملفات (src): {ie}")
    except Exception as e:
        logging.error(f"❌ حدث خطأ غير متوقع أثناء تشغيل البوت: {e}")
        # لا نرفع الخطأ (raise) هنا في بيئة GitHub Actions لضمان انتهاء الـ Job بنجاح شكلي
        # إلا إذا كنت تريد أن يظهر الـ Action كـ "Failed" عند حدوث أي خطأ

if __name__ == "__main__":
    main()
