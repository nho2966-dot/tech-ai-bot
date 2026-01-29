import tweepy
import os
from utils.logger import log

def publish(content):
    client = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )

    if isinstance(content, list):  # ثريد
        tweet_id = None
        for tweet in content:
            res = client.create_tweet(text=tweet, in_reply_to_tweet_id=tweet_id)
            tweet_id = res.data["id"]
        log("🧵 Thread published")
    else:
        client.create_tweet(text=content)
        log("🐦 Tweet published")
