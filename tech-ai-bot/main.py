from src.reply_agent import run_reply_agent
from src.post_publisher import publish_tweet
import logging

if __name__ == "__main__":
    logging.info("--- بدء الدورة البرمجية ---")
    run_reply_agent()
    publish_tweet()
    logging.info("--- نهاية الدورة ---")
