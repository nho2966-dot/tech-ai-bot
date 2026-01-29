import os
import json
import time
import logging
import tweepy
import yaml
from openai import OpenAI
from datetime import datetime

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProFinal:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Hybrid Mode] ---")
        
        # 1. الإعدادات الافتراضية (خطة بديلة)
        self.config = {
            'content': {
                'system_instruction': (
                    "أنت خبير تقني عربي محترف. القواعد: "
                    "1. العربية الفصحى البسيطة فقط (ممنوع الصينية). "
                    "2. الأسلوب تفاعلي وودود. "
                    "3. المد بالواو يتطلب ضم الشفتين جيداً (حاسوب، تكنولوجيا)."
                )
            },
            'api': {
                'openrouter_model': "qwen/qwen-2.5-72b-instruct",
                'reply_model': "openai/gpt-4o-mini"
            },
            'paths': {'state_file': "state.json"}
        }

        # 2. محاولة تحميل YAML إذا وجد بجانب الملف
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.yaml")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    ext_cfg = yaml.safe_load(f)
                    if ext_cfg: self.config.update(ext_cfg)
                    logging.info("✅ External config loaded.")
            except: logging.warning("⚠️ Using internal defaults.")

        # 3. إعداد المصادقة
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        ak, asec = os.environ.get("X_API_KEY"), os.environ.get("X_API_SECRET")
        at, atsec = os.environ.get("X_ACCESS_TOKEN"), os.environ.get("X_ACCESS_SECRET")

        self.client_v2 = tweepy.Client(consumer_key=ak, consumer_secret=asec, access_token=at, access_token_secret=atsec)
        auth = tweepy.OAuth1UserHandler(ak, asec, at, atsec)
        self.api_v1 = tweepy.API(auth)
        
        self.state_path = os.path.join(base_dir, self.config['paths']['state_file'])
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"replied_to": []}

    def run(self):
        try:
            logging.info(f"🕒 UTC Sync: {datetime.utcnow()}")
            # البحث عن تغريدات تقنية عربية
            query = "تقنية OR برمجة lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state["replied_to"]: continue
                    
                    # توليد الرد
                    res = self.ai_client.chat.completions.create(
                        model=self.config['api']['reply_model'],
                        messages=[
                            {"role": "system", "content": self.config['content']['system_instruction']},
                            {"role": "user", "content": f"رد بذكاء: {tweet.text}"}
                        ]
                    )
                    reply_text = res.choices[0].message.content.strip()
                    
                    # تنفيذ الرد عبر v1.1 (أكثر استقراراً للردود)
                    self.api_v1.update_status(
                        status=reply_text[:280],
                        in_reply_to_status_id=tweet.id,
                        auto_populate_reply_metadata=True
                    )
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"✅ Replied to {tweet.id}")
                    break
            
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False)
        except Exception as e:
            logging.error(f"❌ Error: {e}")

if __name__ == "__main__":
    TechExpertProFinal().run()
