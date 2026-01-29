import os
import json
import time
import logging
import tweepy
import yaml
from openai import OpenAI
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProFinal:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Hybrid Config Mode] ---")
        
        # 1. الإعدادات الافتراضية (تعمل في حال فقدان ملف YAML)
        self.config = {
            'content': {
                'system_instruction': (
                    "أنت خبير تقني عربي محترف. القواعد: "
                    "1. العربية الفصحى البسيطة فقط. "
                    "2. الأسلوب تفاعلي ومثير. "
                    "3. المد بالواو يتطلب ضم الشفتين جيداً (مثال: حاسوب، تكنولوجيا)."
                )
            },
            'api': {
                'openrouter_model': "qwen/qwen-2.5-72b-instruct",
                'reply_model': "openai/gpt-4o-mini"
            },
            'paths': {'state_file': "state.json"}
        }

        # 2. محاولة تحميل الإعدادات من ملف خارجي إذا وجد
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    external_config = yaml.safe_load(f)
                    if external_config:
                        self.config.update(external_config)
                        logging.info(f"✅ تم دمج الإعدادات الخارجية من: {config_path}")
            except Exception as e:
                logging.warning(f"⚠️ فشل تحميل الملف الخارجي، سأستخدم الافتراضي: {e}")
        else:
            logging.info("ℹ️ لم يتم العثور على config.yaml، العمل مستمر بالإعدادات المدمجة.")

        # 3. إعداد الاتصالات
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
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
        
        self.state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.config['paths']['state_file'])
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"replied_to": [], "rotation_idx": 0}

    def run(self):
        try:
            logging.info(f"🕒 UTC: {datetime.utcnow()}")
            query = "تقنية OR برمجة lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state.get("replied_to", []): continue
                    
                    res = self.ai_client.chat.completions.create(
                        model=self.config['api']['reply_model'],
                        messages=[
                            {"role": "system", "content": self.config['content']['system_instruction']},
                            {"role": "user", "content": f"رد على: {tweet.text}"}
                        ]
                    )
                    reply = res.choices[0].message.content.strip()
                    
                    self.api_v1.update_status(status=reply[:280], in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True)
                    self.state.setdefault("replied_to", []).append(tweet.id)
                    logging.info(f"✅ تم الرد بنجاح على {tweet.id}")
                    break
                    
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False)
        except Exception as e:
            logging.error(f"❌ خطأ تشغيل: {e}")

if __name__ == "__main__":
    TechExpertProFinal().run()
