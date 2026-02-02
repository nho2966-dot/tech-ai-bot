import tweepy
import requests

class Publisher:
    def __init__(self, keys):
        self.client = tweepy.Client(
            bearer_token=keys['bearer_token'],
            consumer_key=keys['api_key'],
            consumer_secret=keys['api_secret'],
            access_token=keys['access_token'],
            access_token_secret=keys['access_secret']
        )
        # للرفع (Images/Videos)
        auth = tweepy.OAuth1UserHandler(keys['api_key'], keys['api_secret'], keys['access_token'], keys['access_secret'])
        self.api_v1 = tweepy.API(auth)

    def post_content(self, text, media_url=None, poll_options=None):
        media_ids = []
        if media_url:
            # رفع الميديا (صورة أو فيديو)
            media = self.api_v1.media_upload(filename="temp_media", url=media_url)
            media_ids.append(media.media_id)

        return self.client.create_tweet(
            text=text,
            media_ids=media_ids if media_ids else None,
            poll_options=poll_options if poll_options else None
        )

    def reply_smart(self, text, tweet_id):
        return self.client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
