import tweepy
import requests
import os

class Publisher:
    def __init__(self, keys):
        # API V2 للنشر
        self.client = tweepy.Client(
            bearer_token=keys['bearer_token'],
            consumer_key=keys['api_key'],
            consumer_secret=keys['api_secret'],
            access_token=keys['access_token'],
            access_token_secret=keys['access_secret']
        )
        
        # API V1.1 لرفع الوسائط (ضروري للصور والفيديو)
        auth = tweepy.OAuth1UserHandler(
            keys['api_key'], keys['api_secret'],
            keys['access_token'], keys['access_secret']
        )
        self.api_v1 = tweepy.API(auth)

    def post_tweet(self, content, media_url=None, is_video=False):
        try:
            media_ids = []
            
            if media_url:
                media_id = self._upload_media(media_url, is_video)
                if media_id:
                    media_ids.append(media_id)

            # النشر باستخدام API V2 مع ربط الوسائط
            response = self.client.create_tweet(
                text=content,
                media_ids=media_ids if media_ids else None
            )
            
            print(f"✅ تم النشر بنجاح: {content[:50]}...")
            return response.data
            
        except Exception as e:
            print(f"❌ خطأ في النشر: {e}")
            return None

    def _upload_media(self, url, is_video):
        """تحميل الوسائط من رابط ورفعها إلى X"""
        filename = "temp_media.mp4" if is_video else "temp_media.jpg"
        try:
            # تحميل الملف من المصدر
            request = requests.get(url, stream=True)
            if request.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in request.iter_content(1024):
                        f.write(chunk)
                
                # رفع الملف (استخدام simple_upload للصور و chunked للفيديو)
                if is_video:
                    media = self.api_v1.chunked_upload(filename, media_category='tweet_video')
                else:
                    media = self.api_v1.media_upload(filename)
                
                # حذف الملف المؤقت بعد الرفع
                os.remove(filename)
                return media.media_id
            else:
                print(f"⚠️ فشل تحميل الوسائط من الرابط: {url}")
                return None
        except Exception as e:
            print(f"⚠️ خطأ أثناء معالجة الوسائط: {e}")
            if os.path.exists(filename): os.remove(filename)
            return None
