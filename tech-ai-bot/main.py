import os
import json
import time
import random
import logging
import tweepy
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")

logging.basicConfig(level=logging.INFO, format="%(message)s")
ROTATION_KINDS = ["breaking_news", "ai_daily_life", "ai_tool"]

class TechExpertDiversifiedPro:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Premium Logic v2] ---")
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
        
        # استخدام OAuth 1.0a (المفاتيح الأربعة) لضمان أعلى مستوى صلاحيات للمشتركين
        self.auth = tweepy.OAuth1UserHandler(
            os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
            os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"]
        )
        self.api_v1 = tweepy.API(self.auth) # للعمليات التي تتطلب v1.1
        self.client_v2 = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_SECRET"]
        )
        self.state = self._load_state()

    def _load_state(self):
        default = {"replied_to": [], "rotation_idx": 0}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in default.items(): data.setdefault(k, v)
                    return data
            except: pass
        return default

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def handle_smart_replies(self):
        try:
            # البحث عن تغريدات تقنية
            query = "برمجة OR تقنية lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id not in self.state["replied_to"]:
                        res = self.ai_client.chat.completions.create(
                            model="openai/gpt-4o-mini",
                            messages=[{"role": "user", "content": f"رد تقني عربي ذكي ومختصر جداً على: {tweet.text}"}]
                        )
                        reply_text = res.choices[0].message.content.strip()
                        
                        # تنفيذ الرد باستخدام v2 مع ضمان المصادقة
                        self.client_v2.create_tweet(
                            text=reply_text[:280],
                            in_reply_to_tweet_id=tweet.id
                        )
                        self.state["replied_to"].append(tweet.id)
                        logging.info(f"✅ Replied successfully to {tweet.id}")
                        break
        except Exception as e:
            logging.error(f"❌ Smart Reply Logic Error: {e}")

    def execute_diversified_task(self):
        try:
            kind = ROTATION_KINDS[self.state["rotation_idx"] % len(ROTATION_KINDS)]
            self.state["rotation_idx"] += 1
            
            res = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": f"تغريدة تقنية مذهلة عن {kind}"}]
            )
            content = res.choices[0].message.content.strip()
            self.client_v2.create_tweet(text=content[:280])
            logging.info(f"✅ Posted {kind} tweet")
        except Exception as e:
            logging.error(f"❌ Post Error: {e}")

    def run(self):
        self.handle_smart_replies()
        time.sleep(5)
        self.execute_diversified_task()
        self._save_state()

if __name__ == "__main__":
    TechExpertDiversifiedPro().run()
