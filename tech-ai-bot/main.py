import os
import json
import time
import random
import logging
from datetime import datetime
import tweepy
from openai import OpenAI

# إعداد المسارات
B_DIR = os.path.dirname(os.path.abspath(__file__))
S_FILE = os.path.join(B_DIR, "state.json")

logging.basicConfig(level=logging.INFO)

class TechBot:
    def __init__(self):
        # تم الاستغناء عن القائمة التي تسبب SyntaxError واستبدالها بنص بسيط
        self.triggers = "كيف،لماذا،ما،حل،مشكلة".split("،")
        self.ai = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def run(self):
        topic = random.choice(["AI", "Coding", "CyberSecurity"])
        prompt = f"Write a professional Arabic tech thread about {topic}. Separate tweets with '---'."
        
        res = self.ai.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "system", "content": "Tech Expert"}, {"role": "user", "content": prompt}]
        )
        
        tweets = [t.strip() for t in res.choices[0].message.content.split('---') if t.strip()]
        
        p_id = None
        for txt in tweets[:3]: # نشر أول 3 تغريدات فقط للتجربة
            try:
                r = self.x.create_tweet(text=txt, in_reply_to_tweet_id=p_id, user_auth=True)
                p_id = r.data['id']
                time.sleep(2)
            except Exception as e:
                logging.error(e)
        
        with open(S_FILE, "w") as f:
            json.dump({"last": datetime.now().isoformat()}, f)

if __name__ == "__main__":
    TechBot().run()
