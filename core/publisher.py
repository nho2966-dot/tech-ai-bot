import tweepy
import requests
import os

class Publisher:
    def __init__(self, keys):
        # إعداد العميل لـ API v2 (للنشر والردود)
        self.client = tweepy.Client(
            bearer_token=keys.get('bearer_token'),
            consumer_key=keys.get('api_key'),
            consumer_secret=keys.get('api_secret'),
            access_token=keys.get('access_token'),
            access_token_secret=keys.get('access_secret'),
            wait_on_rate_limit=True
        )
        
        # إعداد API v1.1 (ضروري لرفع الصور والفيديوهات)
        auth = tweepy.OAuth1UserHandler(
            keys.get('api_key'), 
            keys.get('api_secret'), 
            keys.get('access_token'), 
            keys.get('access_secret')
        )
        self.api_v1 = tweepy.API(auth)

    def post_content(self, text, media_url=None, is_poll=False):
        """نشر تغريدة، ثريد، أو استطلاع رأي مع دعم الوسائط"""
        try:
            media_ids = []
            if media_url and not is_poll:
                # تحميل الصورة مؤقتاً ورفعها
                img_data = requests.get(media_url).content
                with open('temp_image.jpg', 'wb') as handler:
                    handler.write(img_data)
                
                media = self.api_v1.media_upload('temp_image.jpg')
                media_ids = [media.media_id]
                os.remove('temp_image.jpg')

            # النشر عبر API v2
            if is_poll:
                # خيارات الاستطلاع الافتراضية إذا كان نوع المنشور Poll
                return self.client.create_tweet(
                    text=text,
                    poll_options=["نعم، أتفق", "لا أتفق", "ربما مستقبلاً", "أحتاج تفاصيل أكثر"],
                    poll_duration_minutes=1440 # 24 ساعة
                )
            else:
                return self.client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
        except Exception as e:
            print(f"❌ خطأ في النشر: {e}")
            return False

    def get_recent_mentions(self):
        """جلب الإشارات (Mentions) الأخيرة للرد عليها"""
        try:
            bot_id = self.client.get_me().data.id
            mentions = self.client.get_users_mentions(id=bot_id, expansions='author_id')
            return mentions.data if mentions.data else []
        except Exception as e:
            print(f"⚠️ خطأ في جلب المنشنز: {e}")
            return []

    def reply_to_tweet(self, text, tweet_id):
        """الرد على تغريدة محددة"""
        try:
            return self.client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
        except Exception as e:
            print(f"❌ خطأ في الرد: {e}")
            return False
