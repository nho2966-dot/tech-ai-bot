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
        logging.info("--- Tech Expert Pro [Hybrid Mode Activated] ---")
        
        # 1. الإعدادات الافتراضية (تعمل إذا فُقد ملف YAML)
        self.config = {
            'content': {
                'system_instruction': (
                    "أنت خبير تقني عربي محترف. القواعد: "
                    "1. العربية الفصحى البسيطة فقط. "
                    "2. الأسلوب تفاعلي ومثير وغير جاف. "
                    "3. المد بالواو يتطلب ضم الشفتين جيداً (مثال: حاسوب، تكنولوجيا)."
                )
            },
            'api': {
                'openrouter_model': "qwen/qwen-2.5-72b-instruct",
                'reply_model': "openai/gpt-4o-mini"
            },
            'paths': {'state_file': "state.json"}
        }

        # 2. محاولة ذكية للعثور على ملف الإعدادات الخارجي
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.yaml")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    ext_cfg = yaml.safe_load(f)
                    if ext_cfg:
                        self.config.update(ext_cfg)
                        logging.info(f"✅ تم دمج الإعدادات من: {config_path}")
            except Exception as e:
                logging.warning(f"⚠️ فشل قراءة الملف، سأستخدم الافتراضي: {e}")
        else:
            logging.info("ℹ️ لم يتم العثور على config.yaml، سأعمل بالإعدادات المدمجة.")

        # 3. إعداد الاتصالات (X و AI)
        try:
            self.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY")
            )
            
            # مفاتيح X
            api_key = os.environ.get("X_API_KEY")
            api_secret = os.environ.get("X_API_SECRET")
            access_token = os.environ.get("X_ACCESS_TOKEN")
            access_secret = os.environ.get("X_ACCESS_SECRET")

            self.client_v2 = tweepy.Client(
                consumer_key=api_key, consumer_secret=api_secret,
                access_token=access_token, access_token_secret=access_secret
            )
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            self.api_v1 = tweepy.API(auth)
            
            self.state_path = os.path.join(base_dir, self.config['paths']['state_file'])
            self.state = self._load_state()
        except Exception as e:
            logging.error(f"❌ خطأ في إعداد المفاتيح: {e}")
            raise

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"replied_to": [], "rotation_idx": 0}

    def run(self):
        try:
            logging.info(f"🕒 توقيت التشغيل (UTC): {datetime.utcnow()}")
            # البحث عن تغريدات لرد ذكي
            query = "تقنية OR ذكاء_اصطناعي lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state.get("replied_to", []): continue
                    
                    # توليد الرد بذكاء
                    res = self.ai_client.chat.completions.create(
                        model=self.config['api']['reply_model'],
                        messages=[
                            {"role": "system", "content": self.config['content']['system_instruction']},
                            {"role": "user", "content": f"رد على هذه التغريدة بأسلوب خبير: {tweet.text}"}
                        ]
                    )
                    reply = res.choices[0].message.content.strip()
                    
                    # الرد الفعلي
                    self.api_v1.update_status(
                        status=reply[:280], 
                        in_reply_to_status_id=tweet.id, 
                        auto_populate_reply_metadata=True
                    )
                    self.state.setdefault("replied_to", []).append(tweet.id)
                    logging.info(f"✅ تم الرد بنجاح على التغريدة: {tweet.id}")
                    break # رد واحد في كل دورة لتجنب الحظر
            
            # حفظ الحالة
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False)
        except Exception as e:
            logging.error(f"❌ خطأ أثناء التشغيل: {e}")

if __name__ == "__main__":
    TechExpertProFinal().run()
