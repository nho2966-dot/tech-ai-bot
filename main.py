import os
import json
import logging
import tweepy
from openai import OpenAI

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

def run_bot():
    logging.info("🚀 تشغيل البوت للحساب المدفوع عبر API v2...")
    
    # 1. جلب المفاتيح وتنظيفها
    keys = {
        "ck": os.environ.get("X_API_KEY", "").strip(),
        "cs": os.environ.get("X_API_SECRET", "").strip(),
        "at": os.environ.get("X_ACCESS_TOKEN", "").strip(),
        "as": os.environ.get("X_ACCESS_SECRET", "").strip(),
        "ai": os.environ.get("OPENROUTER_API_KEY", "").strip()
    }

    try:
        # 2. الاتصال بـ X (API v2 هو الأضمن للمشتركين)
        client = tweepy.Client(
            consumer_key=keys["ck"], consumer_secret=keys["cs"],
            access_token=keys["at"], access_token_secret=keys["as"]
        )
        
        # التأكد من هوية الحساب
        me = client.get_me()
        logging.info(f"✅ متصل بنجاح كـ: {me.data.username}")

        # 3. إعداد الذكاء الاصطناعي
        ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=keys["ai"])

        # 4. البحث (استهداف تقني ذكي)
        query = "(تكنولوجيا OR ذكاء_اصطناعي OR برمجة) lang:ar -is:retweet -is:reply"
        tweets = client.search_recent_tweets(query=query, max_results=5)

        if tweets.data:
            # تحميل ملف الحالة من المسار الصحيح
            state_file = "state.json"
            replied_to = []
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    replied_to = json.load(f).get("replied", [])

            for tweet in tweets.data:
                if tweet.id in replied_to: continue
                
                # توليد الرد (مع الالتزام بالمد بالواو والاحترافية)
                prompt = f"رد بذكاء كخبير تقني عربي (استخدم المد بالواو مثل: حاسووووب، تكنولوجياااا) على: {tweet.text}"
                response = ai_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                reply_text = response.choices[0].message.content.strip()

                # إرسال الرد عبر v2
                client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                replied_to.append(tweet.id)
                logging.info(f"✅ تم الرد على التغريدة {tweet.id}")
                
                # حفظ الحالة فوراً
                with open(state_file, "w") as f:
                    json.dump({"replied": replied_to}, f)
                break # رد واحد لكل تشغيل لضمان الجودة
        else:
            logging.info("🔎 لا توجد تغريدات تقنية جديدة حالياً.")

    except Exception as e:
        logging.error(f"❌ حدث خطأ (تحقق من تطابق المفاتيح): {e}")

if __name__ == "__main__":
    run_bot()
