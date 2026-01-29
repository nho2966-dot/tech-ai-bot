import os
import json
import time
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعداد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProFinal:
    def __init__(self):
        # 1. إعداد الذكاء الاصطناعي مع تعليماتك اللغوية
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        # 2. إعداد المصادقة الهجينة (تأكد من تحديث السكرت في جيتهاب)
        self.api_key = os.environ.get("X_API_KEY")
        self.api_secret = os.environ.get("X_API_SECRET")
        self.access_token = os.environ.get("X_ACCESS_TOKEN")
        self.access_secret = os.environ.get("X_ACCESS_SECRET")

        # عميل V2 للنشر والبحث
        self.client_v2 = tweepy.Client(
            consumer_key=self.api_key, consumer_secret=self.api_secret,
            access_token=self.access_token, access_token_secret=self.access_secret
        )

        # عميل V1.1 للردود (OAuth 1.0a)
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

    def handle_replies(self):
        """الرد الذكي - معالجة خطأ 401 المحتمل من فارق التوقيت"""
        try:
            # التحقق من الوقت الحالي (للتأكد من المزامنة في السجلات)
            logging.info(f"Current Server Time (UTC): {datetime.utcnow()}")
            
            query = "تقنية OR ذكاء_اصطناعي lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state["replied_to"]: continue
                    
                    # توليد المحتوى العربي (مع مراعاة ضم الشفتين في المد بالواو)
                    res = self.ai_client.chat.completions.create(
                        model="openai/gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "أنت خبير تقني عربي. رد بأسلوب ودود ومختصر جداً بالعربية فقط."},
                            {"role": "user", "content": f"رد على: {tweet.text}"}
                        ]
                    )
                    reply_text = res.choices[0].message.content.strip()

                    # الرد عبر V1.1
                    self.api_v1.update_status(
                        status=reply_text[:280],
                        in_reply_to_status_id=tweet.id,
                        auto_populate_reply_metadata=True
                    )
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"✅ Successfully replied to {tweet.id}")
                    break
        except Exception as e:
            logging.error(f"❌ Reply Logic Error: {e}")

    def run(self):
        self.handle_replies()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False)

if __name__ == "__main__":
    TechExpertProFinal().run()
