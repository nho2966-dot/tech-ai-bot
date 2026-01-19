import os
import tweepy
from google import genai
import logging
import time

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)

def process_mentions():
    try:
        # 1. إعداد عميل X (Twitter)
        # نحتاج هنا إلى Client (للنشر) و API (للبحث عن الردود)
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        api_old = tweepy.API(auth)
        client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # 2. الحصول على آخر منشن (Mentions)
        # سنكتفي بآخر 5 منشنز لتجنب الزحام
        mentions = api_old.mentions_timeline(count=5)
        
        if not mentions:
            logging.info("💡 لا توجد إشارات (Mentions) جديدة للرد عليها حالياً.")
            return

        # 3. إعداد Gemini للرد
        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))

        for mention in mentions:
            logging.info(f"🔍 جاري معالجة منشن من: {mention.user.screen_name}")
            
            # منع البوت من الرد على نفسه
            if mention.user.screen_name.lower() == "X_TechNews_".lower(): # استبدل بـ ID حسابك
                continue

            # توليد رد ذكي
            prompt = f"""
            أنت خبير تقني ذكي وودود. وصلك منشن من مستخدم يقول: "{mention.text}"
            اكتب رداً قصيراً، ذكياً، ومحفزاً للمتابعة بالعربية الفصحى البسيطة.
            استخدم إيموجي مناسباً. لا تتجاوز 140 حرفاً.
            """
            
            response = client_ai.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )

            if response and response.text:
                reply_text = f"@{mention.user.screen_name} {response.text.strip()}"
                
                # إرسال الرد
                client_v2.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=mention.id
                )
                logging.info(f"✅ تم الرد على {mention.user.screen_name}")
                time.sleep(5) # فاصلاً زمنياً بسيطاً بين الردود

    except Exception as e:
        logging.error(f"❌ خطأ في نظام الردود: {e}")

if __name__ == "__main__":
    process_mentions()
