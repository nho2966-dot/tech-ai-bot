import os
import json
import time
import logging
import tweepy
import yaml
from openai import OpenAI
from datetime import datetime

# إعداد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProFinal:
    def __init__(self):
        logging.info("--- Tech Expert Pro [NTP Sync & Hybrid Auth] ---")
        
        # تحميل الإعدادات من YAML
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 1. إعداد الذكاء الاصطناعي
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        # 2. إعداد المصادقة
        self.api_key = os.environ.get("X_API_KEY")
        self.api_secret = os.environ.get("X_API_SECRET")
        self.access_token = os.environ.get("X_ACCESS_TOKEN")
        self.access_secret = os.environ.get("X_ACCESS_SECRET")

        # التحقق من وجود المفاتيح
        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            logging.error("❌ مفقود: أحد مفاتيح X API. تأكد من إضافتها في GitHub Secrets.")

        # عميل V2 (للنشر والبحث)
        self.client_v2 = tweepy.Client(
            consumer_key=self.api_key, consumer_secret=self.api_secret,
            access_token=self.access_token, access_token_secret=self.access_secret
        )

        # عميل V1.1 (للردود - OAuth 1.0a)
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

    def _save_state(self):
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def handle_replies(self):
        """الرد الذكي مع مراقبة وقت السيرفر"""
        try:
            # تسجيل وقت السيرفر للتأكد من المزامنة
            server_time = datetime.utcnow()
            logging.info(f"🕒 Server Time (UTC): {server_time}")
            
            query = "تقنية OR برمجة lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state.get("replied_to", []): continue
                    
                    # توليد المحتوى
                    res = self.ai_client.chat.completions.create(
                        model=self.config['api']['reply_model'],
                        messages=[
                            {"role": "system", "content": self.config['content']['system_instruction']},
                            {"role": "user", "content": f"رد بذكاء وود على: {tweet.text}"}
                        ]
                    )
                    reply_text = res.choices[0].message.content.strip()

                    # تنفيذ الرد عبر V1.1 لتجنب 401 (v2)
                    self.api_v1.update_status(
                        status=reply_text[:280],
                        in_reply_to_status_id=tweet.id,
                        auto_populate_reply_metadata=True
                    )
                    self.state.setdefault("replied_to", []).append(tweet.id)
                    logging.info(f"✅ تم الرد بنجاح على التغريدة {tweet.id}")
                    break
        except Exception as e:
            logging.error(f"❌ خطأ في الردود: {e}")

    def run(self):
        self.handle_replies()
        # فجوة زمنية بسيطة لتجنب الـ Rate Limit
        time.sleep(20)
        # يمكنك إضافة دالة النشر هنا أيضاً بنفس الطريقة
        self._save_state()

if __name__ == "__main__":
    TechExpertProFinal().run()
