import os
import tweepy
import requests
import logging
import random
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(message)s')
load_dotenv()

# إعداد Client لـ X API V2
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

def get_ai_reply(user_name, user_text):
    """توليد رد ذكي وفصيح باستخدام الذكاء الاصطناعي"""
    prompt = (
        f"أنت خبير تقني ودود. وصلك منشن من المستخدم {user_name} يقول فيه: '{user_text}'.\n"
        "اكتب رداً ذكياً، قصيراً، وبالعربية الفصحى.\n"
        "شجع المستخدم، أجب على سؤاله إذا وجد، وأضف لمسة من الخبرة التقنية.\n"
        "لا تزد عن 200 حرف."
    )
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except:
        return f"أهلاً بك يا {user_name}! يسعدني تواصلك التقني. دعنا نستمر في استكشاف آفاق الابتكار معاً. 🚀"

def reply_to_mentions():
    """البحث عن المنشنز والرد عليها"""
    try:
        # الحصول على ID الحساب الخاص بك أولاً
        me = client.get_me()
        my_id = me.data.id
        
        # جلب آخر المنشنز (آخر 5 لتجنب استهلاك الكوتا)
        mentions = client.get_users_mentions(id=my_id, max_results=5)
        
        if not mentions.data:
            logging.info("ℹ️ لا توجد منشنز جديدة حالياً.")
            return

        for tweet in mentions.data:
            logging.info(f"💬 معالجة المنشن من ID: {tweet.id}")
            
            # توليد الرد
            reply_text = get_ai_reply("صديقي المبدع", tweet.text)
            
            # النشر كرد
            client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
            logging.info(f"✅ تم الرد بنجاح على: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ في نظام الردود: {e}")

if __name__ == "__main__":
    # تشغيل نظام النشر الرئيسي (الذي صممناه سابقاً)
    # ثم تشغيل نظام الردود
    logging.info("🤖 بدء عمل البوت المتكامل (نشر + ردود)...")
    reply_to_mentions()
