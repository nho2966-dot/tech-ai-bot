import os
from dotenv import load_dotenv
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# تحميل المتغيرات من .env (اختياري)
load_dotenv()

def main():
    # استيراد الوحدات
    from post_publisher import publish_tech_tweet
    from reply_agent import process_mentions

    # النشر
    publish_tech_tweet()

    # الردود
    BOT_USERNAME = os.getenv("BOT_USERNAME", "TechAI_Bot")
    process_mentions(BOT_USERNAME)

if __name__ == "__main__":
    main()
