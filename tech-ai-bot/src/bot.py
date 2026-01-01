# src/bot.py
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

def main():
    from post_publisher import publish_tech_tweet
    publish_tech_tweet()

    from reply_agent import process_mentions
    BOT_USERNAME = os.getenv("BOT_USERNAME", "TechAI_Bot")
    process_mentions(BOT_USERNAME)

if __name__ == "__main__":
    main()