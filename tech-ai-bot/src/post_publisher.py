import os
import tweepy
from google import genai
import logging
import time

# إعداد التسجيل لمراقبة أداء البوت
logging.basicConfig(level=logging.INFO)

def publish_tech_tweet():
    try:
        # 1. إعداد عميل Gemini 2.0
        client_ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        
        prompt = "أعطني معلومة تقنية مذهلة وجديدة عن الذكاء الاصطناعي في عام 2026 لتغريدة عربية مشوقة مع هاشتاقات تقنية."
        
        # 2. آلية إعادة المحاولة في حال وجود زحام (خطأ 429)
        response = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logging.info(f"🔄 محاولة توليد المحتوى (محاولة رقم {attempt + 1})...")
                response = client_ai.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt
                )
                break  # نجحت العملية، اخرج من حلقة التكرار
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 20  # انتظار تصاعدي: 20، 40 ثانية
                    logging.warning(f"⚠️ زحام في السيرفر، سأنتظر {wait_time} ثانية...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e

        if not response or not response.text:
            raise Exception("لم يتم توليد نص من Gemini")

        tweet_text = response.text.strip()

        # 3. إعداد عميل X (Twitter)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # 4. نشر التغريدة (مع قص النص إذا تجاوز الحد المسموح)
        client.create_tweet(text=tweet_text[:280])
        logging.info("✅ تم نشر التغريدة التقنية بنجاح على حسابك.")

    except Exception as e:
        logging.error(f"❌ فشل نظام النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
