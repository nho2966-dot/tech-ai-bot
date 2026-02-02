import tweepy

class Publisher:
    def __init__(self, keys):
        self.client = tweepy.Client(
            bearer_token=keys['bearer_token'],
            consumer_key=keys['api_key'],
            consumer_secret=keys['api_secret'],
            access_token=keys['access_token'],
            access_token_secret=keys['access_secret']
        )

    def post_tweet(self, content):
        try:
            # بفضل اشتراك X، نرسل المحتوى كاملاً
            response = self.client.create_tweet(text=content)
            print(f"✅ تم النشر بنجاح: {content[:50]}...")
            return response.data
        except Exception as e:
            print(f"❌ خطأ في النشر: {e}")
            return None
