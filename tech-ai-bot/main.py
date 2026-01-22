import os
import tweepy
import requests
import logging
import random
import re
from datetime import datetime
import pytz
from dotenv import load_dotenv

# ✅ إعدادات النخبة
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MASTER-AI] - %(message)s')

client = tweepy.Client(
    bearer_token=os.getenv("X_BEARER_TOKEN"),
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

ARCHIVE_FILE = "published_archive.txt"

def is_duplicate(identifier):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return identifier.lower()[:60] in f.read().lower()

def save_to_archive(identifier):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {identifier}\n")

def generate_ai_content(prompt_type, context_data="", username=""):
    try:
        system_persona = (
            "أنت 'Cyber Hunter'. خبير تقني ودود وحاسم. "
            "قاعدة صارمة: يجب أن يكون ردك كاملاً ومختصراً جداً (أقل من 240 حرفاً). "
            "الهيكل: تحية -> معلومة دسمة ومختصرة -> سؤال مباشر للمتابع."
        )
        
        user_msg = f"رد على @{username}: {context_data}" if prompt_type == "reply" else f"اكتب تغريدة عن: {context_data}"

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "system", "content": system_persona}, {"role": "user", "content": user_msg}],
                "max_tokens": 150 # تقليل التوكنز لضمان الاختصار وعدم البتر
            }, timeout=45
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ AI Error: {e}")
        return None

def auto_reply():
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
        
        if not mentions or not mentions.data:
            logging.info("🔎 لا منشنات جديدة.")
            return

        # إنشاء قاموس لأسماء المستخدمين
        users = {u['id']: u['username'] for u in mentions.includes['users']}

        for tweet in mentions.data:
            reply_id = f"reply_{tweet.id}"
            if is_duplicate(reply_id): continue
            
            author_username = users.get(tweet.author_id)
            reply_text = generate_ai_content("reply", tweet.text, author_username)
            
            if reply_text:
                # إضافة المنشن في بداية النص لضمان الربط بـوُضُـوح
                final_text = f"@{author_username} {reply_text}"
                client.create_tweet(
                    text=final_text[:280], 
                    in_reply_to_tweet_id=tweet.id # هذا السطر هو المسؤول عن جعلها 'رد' وليس تغريدة مستقلة
                )
                save_to_archive(reply_id)
                logging.info(f"✅ تم الرد بنجاح على {author_username}")
    except Exception as e:
        logging.error(f"❌ فشل الرد: {e}")

if __name__ == "__main__":
    auto_reply()
    # يمكنك تفعيل post_scoop() هنا إذا أردت نشر تغريدات دورية أيضاً
