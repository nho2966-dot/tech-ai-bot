import sys
import os
import logging

# إضافة مسار src للنظام لضمان الاستيراد الصحيح
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from post_publisher import publish_tech_tweet
    from reply_agent import run_reply_agent
except ImportError as e:
    logging.error(f"❌ خطأ في الاستيراد: {e}")

if __name__ == "__main__":
    # هذا الملف سيتم استدعاؤه بواسطة YAML للنشر
    publish_tech_tweet()
