import os
import tweepy
from google import genai
import logging
import time

# إعداد التسجيل ليكون واضحاً في GitHub Actions
logging.basicConfig(level=logging.INFO)

def process_mentions():
    try:
        logging.info("🔍 فحص التعليقات والإشارات (Mentions) الجديدة...")
        
        # 1. إعداد الاتصال بـ X (نحتاج v1.1 لقراءة المنشن و v2 للرد)
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        api_v1 = tweepy.API(auth)
        client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # 2. جلب آخر 5 إشارات
        mentions = api_v1.mentions_timeline(count=5)
        
        if not mentions:
            logging.info("💡 لا توجد تعليقات جديدة للرد عليها.")
            return

        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))

        for mention in mentions:
            logging.info(f"📩 تعليق جديد من: {mention.user.screen_name}")
            
            # منع الرد المتكرر أو الرد على النفس
            # ملاحظة: تأكد من تغيير ID حسابك ليتناسب مع حسابك الفعلي
            
            prompt = f"""
            أنت خبير تقني ودود. رد على هذا التعليق: "{mention.text}"
            بأسلوب ذكي، فصيح، ومختصر جداً (أقل من 140 حرفاً). 
            استخدم لغة عربية سليمة وإيموجي واحد.
            """
            
            response = client_ai.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )

            if response and response.text:
                reply_text = f"@{mention.user.screen_name} {response.text.strip()}"
                
                # إرسال الرد عبر API v2
                client_v2.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=mention.id
                )
                logging.info(f"✅ تم الرد بنجاح على @{mention.user.screen_name}")
                time.sleep(2) # تجنب الحظر

    except Exception as e:
        logging.error(f"❌ خطأ في نظام الردود: {e}")

if __name__ == "__main__":
    process_mentions()
