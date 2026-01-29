import os
import json
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعداد السجلات لمتابعة الأداء من GitHub Actions
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

def run_bot():
    logging.info("🚀 بدء تشغيل البوت المحدث للحساب المدفوع...")
    
    # 1. جلب المفاتيح بعد التحديث (مع التنظيف التلقائي للفراغات)
    keys = {
        "ck": os.environ.get("X_API_KEY", "").strip(),
        "cs": os.environ.get("X_API_SECRET", "").strip(),
        "at": os.environ.get("X_ACCESS_TOKEN", "").strip(),
        "as": os.environ.get("X_ACCESS_SECRET", "").strip(),
        "ai": os.environ.get("OPENROUTER_API_KEY", "").strip()
    }

    try:
        # 2. إعداد الاتصال بـ X (نستخدم Client v2 للحسابات المدفوعة)
        client = tweepy.Client(
            consumer_key=keys["ck"],
            consumer_secret=keys["cs"],
            access_token=keys["at"],
            access_token_secret=keys["as"],
            wait_on_rate_limit=True
        )
        
        # التحقق من الاتصال واسم الحساب
        me = client.get_me()
        logging.info(f"✅ متصل بنجاح كـ: {me.data.username}")

        # 3. إعداد محرك الذكاء الاصطناعي
        ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=keys["ai"]
        )

        # 4. البحث الاستهدافي (تكنولوجيا، برمجة، ذكاء اصطناعي)
        # استبعاد الريتويت والردود لضمان جودة الاستهداف
        query = "(تكنولوجيا OR ذكاء_اصطناعي OR برمجة OR تقنية) lang:ar -is:retweet -is:reply"
        
        # استخدام user_auth=True لحل مشكلة الصلاحيات في الحسابات المدفوعة
        tweets = client.search_recent_tweets(
            query=query, 
            max_results=5,
            user_auth=True 
        )

        if tweets.data:
            # إدارة حالة الردود لتجنب التكرار
            state_file = "state.json"
            replied_to = []
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r") as f:
                        replied_to = json.load(f).get("replied", [])
                except: pass

            for tweet in tweets.data:
                if tweet.id in replied_to: continue
                
                logging.info(f"📝 جاري صياغة رد على تغريدة: {tweet.id}")

                # 5. توليد الرد (الالتزام باللغة العربية والمد بالواو)
                system_msg = (
                    "أنت خبير تقني محترف. رد بذكاء واختصار باللغة العربية. "
                    "تذكر دائماً: المد بالواو يتطلب ضم الشفتين جيداً (مثال: حاسووووب، تكنولوجياااا، مطوووور)."
                )
                
                response = ai_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": f"رد كخبير على: {tweet.text}"}
                    ]
                )
                reply_text = response.choices[0].message.content.strip()

                # 6. إرسال الرد عبر API v2
                client.create_tweet(
                    text=reply_text[:280], 
                    in_reply_to_tweet_id=tweet.id,
                    user_auth=True
                )
                
                replied_to.append(tweet.id)
                logging.info(f"✅ تم الرد بنجاح على التغريدة!")
                
                # حفظ الحالة
                with open(state_file, "w") as f:
                    json.dump({"replied": replied_to}, f)
                
                # الرد على تغريدة واحدة في كل دورة للحفاظ على أمان الحساب
                break 
        else:
            logging.info("🔎 لم يتم العثور على تغريدات جديدة حالياً.")

    except Exception as e:
        logging.error(f"❌ خطأ تقني: {e}")

if __name__ == "__main__":
    run_bot()
