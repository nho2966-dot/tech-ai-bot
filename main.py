import os
import json
import time
import logging
import tweepy
import yaml
from openai import OpenAI
from datetime import datetime

# إعداد المسارات الديناميكية (تكتشف مكان الملف تلقائياً)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
STATE_FILE = os.path.join(BASE_DIR, "state.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProFinal:
    def __init__(self):
        logging.info(f"--- Tech Expert Pro [Smart Paths Activated] ---")
        logging.info(f"🔍 Searching for config at: {CONFIG_PATH}")
        
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(f"❌ config.yaml not found at {CONFIG_PATH}")
            
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # إعداد AI
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        # إعداد X
        self.api_key = os.environ.get("X_API_KEY")
        self.api_secret = os.environ.get("X_API_SECRET")
        self.access_token = os.environ.get("X_ACCESS_TOKEN")
        self.access_secret = os.environ.get("X_ACCESS_SECRET")

        self.client_v2 = tweepy.Client(
            consumer_key=self.api_key, consumer_secret=self.api_secret,
            access_token=self.access_token, access_token_secret=self.access_secret
        )
        auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret, self.access_token, self.access_secret)
        self.api_v1 = tweepy.API(auth)
        
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"replied_to": [], "rotation_idx": 0}

    def generate_content(self, prompt, is_reply=False):
        model = self.config['api']['reply_model'] if is_reply else self.config['api']['openrouter_model']
        res = self.ai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.config['content']['system_instruction']},
                {"role": "user", "content": prompt}
            ]
        )
        return res.choices[0].message.content.strip()

    def handle_replies(self):
        try:
            logging.info(f"🕒 UTC Time: {datetime.utcnow()}")
            query = "تقنية OR برمجة lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state["replied_to"]: continue
                    reply = self.generate_content(f"رد على: {tweet.text}", is_reply=True)
                    self.api_v1.update_status(status=reply[:280], in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True)
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"✅ Replied to {tweet.id}")
                    break
        except Exception as e:
            logging.error(f"❌ Reply Error: {e}")

    def run(self):
        self.handle_replies()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False)

if __name__ == "__main__":
    TechExpertProFinal().run()
