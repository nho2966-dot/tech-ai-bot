import os
import logging
from src.post_publisher import publish_tech_tweet
from src.reply_agent import process_mentions

# إعداد السجلات
if not os.path.exists("logs"): os.makedirs("logs")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler("logs/bot.log", encoding='utf-8'), logging.StreamHandler()]
)

def main():
    logging.info("🚀 بدء تشغيل المنظومة الموحدة...")
    
    # 1. الردود
    bot_username = os.getenv("BOT_USERNAME")
    if bot_username:
        process_mentions(bot_username)
    
    # 2. النشر
    publish_tech_tweet()

    logging.info("🏁 تمت جميع العمليات بنجاح.")

if __name__ == "__main__":
    main()
