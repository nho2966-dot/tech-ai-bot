import logging
import sys
from src.reply_agent import run_reply_agent
from src.post_publisher import publish_tweet

# إعداد التسجيل لرؤية المخرجات في GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    logging.info("🚀 بدء تشغيل المنظومة التقنية المتكاملة...")

    # 1. تشغيل نظام الردود الذكية
    try:
        logging.info("🔎 جاري فحص المنشن والردود...")
        run_reply_agent()
        logging.info("✅ انتهى نظام الردود من العمل.")
    except Exception as e:
        logging.error(f"❌ فشل في نظام الردود: {e}")

    print("-" * 30)

    # 2. تشغيل نظام النشر الاحترافي (نمط LTPO)
    try:
        logging.info("📝 جاري توليد ونشر التغريدة الاحترافية...")
        publish_tweet()
        logging.info("✅ انتهى نظام النشر من العمل.")
    except Exception as e:
        logging.error(f"❌ فشل في نظام النشر: {e}")

    logging.info("🏁 تمت جميع المهام بنجاح.")

if __name__ == "__main__":
    main()
