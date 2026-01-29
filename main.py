import os
import json
import logging
import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

def run_bot():
    logging.info("🚀 تشغيل نسخة الربط الثنائي...")
    
    # جلب المفاتيح
    ck = os.environ.get("X_API_KEY", "").strip()
    cs = os.environ.get("X_API_SECRET", "").strip()
    at = os.environ.get("X_ACCESS_TOKEN", "").strip()
    as_ = os.environ.get("X_ACCESS_SECRET", "").strip()
    bt = os.environ.get("X_BEARER_TOKEN", "").strip() # تأكد من إضافة هذا في Secrets

    try:
        # الاتصال باستخدام Bearer Token للبحث (أكثر استقراراً للبحث)
        client = tweepy.Client(
            bearer_token=bt,
            consumer_key=ck, consumer_secret=cs,
            access_token=at, access_token_secret=as_,
            wait_on_rate_limit=True
        )

        # 4. البحث (استهداف تقني)
        query = "(تكنولوجيا OR ذكاء_اصطناعي) lang:ar -is:retweet -is:reply"
        # جربنا البحث بدون user_auth أولاً باستخدام الـ Bearer
        tweets = client.search_recent_tweets(query=query, max_results=5)

        if tweets.data:
            state_file = "state.json"
            replied_to = []
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    replied_to = json.load(f).get("replied", [])

            for tweet in tweets.data:
                if tweet.id in replied_to: continue
                
                # إرسال الرد
                client.create_tweet(text=f"تكنولوجياااا مذهلة! حاسووووب المستقبل هنا. #ذكاء_اصطناعي", in_reply_to_tweet_id=tweet.id)
                
                replied_to.append(tweet.id)
                with open(state_file, "w") as f:
                    json.dump({"replied": replied_to}, f)
                logging.info(f"✅ نجحت المهمة! تم الرد على: {tweet.id}")
                break
        else:
            logging.info("🔎 لا توجد نتائج.")

    except Exception as e:
        logging.error(f"❌ الخطأ المستمر: {e}")

if __name__ == "__main__":
    run_bot()
