import os
import tweepy
import requests
import logging
import random
import re
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv

# ✅ إعدادات النخبة والـوُضُـوح
load_dotenv()
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [MASTER-AI] - %(message)s',
    handlers=[logging.FileHandler("agent.log", encoding='utf-8'), logging.StreamHandler()]
)

# ✅ تهيئة الوصول لمنصة X
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

ARCHIVE_FILE = "published_archive.txt"

def is_duplicate(identifier):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return identifier.lower()[:60] in f.read().lower()

def save_to_archive(identifier):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {identifier}\n")

def generate_ai_content(prompt_type, context_data=""):
    try:
        system_persona = (
            "أنت 'Cyber Hunter' - خبير استخبارات تقنية. "
            "القواعد: مصادر موثوقة (CVE, GitHub, TechCrunch)، صرامة تقنية، "
            "هيكل: [TITLE] -> Hook -> 3 نقاط دسمة -> تلميحة -> رابط مصدر -> #هاشتاج."
        )
        user_msg = f"انشر سبقاً حول: {context_data}" if prompt_type == "post" else f"رد بذكاء على: {context_data}"
        
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "system", "content": system_persona}, {"role": "user", "content": user_msg}],
                "temperature": 0.5
            }, timeout=30
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ AI Error: {e}")
        return None

def post_scoop():
    topic = random.choice(["ثغرات أمنية حرجة", "تسريبات هواتف", "ذكاء اصطناعي"])
    content = generate_ai_content("post", topic)
    if not content or "TITLE:" not in content or "http" not in content: return
    
    title = re.search(r"TITLE: (.*)\n", content).group(1).strip()
    if is_duplicate(title): return
    
    client.create_tweet(text=content.replace(f"TITLE: {title}", "").strip()[:280])
    save_to_archive(title)
    logging.info(f"✅ تم النشر: {title}")

def auto_reply():
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(id=me.id, max_results=5)
        if not mentions.data: return
        for tweet in mentions.data:
            if is_duplicate(f"reply_{tweet.id}"): continue
            reply = generate_ai_content("reply", tweet.text)
            if reply:
                client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                save_to_archive(f"reply_{tweet.id}")
                logging.info(f"💬 تم الرد على: {tweet.id}")
    except Exception as e:
        logging.error(f"❌ Reply Error: {e}")

if __name__ == "__main__":
    oman_tz = pytz.timezone('Asia/Muscat')
    now = datetime.now(oman_tz)
    if now.hour in [9, 12, 16, 20, 23]:
        post_scoop()
    auto_reply()
