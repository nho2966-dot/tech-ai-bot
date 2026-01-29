import os
import json
import time
import logging
import yaml
import tweepy
from openai import OpenAI
from datetime import datetime, timezone

# --- إعدادات المسارات ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class TechExpertMasterFinal:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Arabic Optimized v90] ---")
        
        # 1. الاتصال بـ OpenAI/OpenRouter مع تعزيز "شخصية البوت"
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        # 2. المصادقة المزدوجة (V1 للردود و V2 للنشر) لحل 401 نهائياً
        self.auth = tweepy.OAuth1UserHandler(
            os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
            os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"]
        )
        self.api_v1 = tweepy.API(self.auth)
        self.client_v2 = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_SECRET"]
        )
        
        self.state = self._load_state()
        self.rotation_kinds = ["breaking_news", "ai_daily_life", "ai_tool"]

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

    def generate_content(self, prompt, model="qwen/qwen-2.5-72b-instruct"):
        """توليد محتوى عربي بأسلوب بشري غير جاف ومكتمل"""
        try:
            response = self.ai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "أنت خبير تقني عربي وصانع محتوى بارع. "
                            "تحدث بلغة عربية فصحى بسيطة وودودة. "
                            "تجنب الجفاف، استخدم أسلوباً مشوقاً، وتأكد من اكتمال الفكرة. "
                            "ممنوع تماماً استخدام أي لغة غير العربية."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250 # لضمان عدم قطع النص
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            return None

    def handle_targeting_replies(self):
        """الرد الذكي باستخدام V1.1 لتجنب 401"""
        try:
            # البحث عبر V2
            query = "تقنية OR ذكاء_اصطناعي lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state["replied_to"]: continue
                    
                    prompt = f"اكتب رداً ذكياً ومختصراً جداً على هذه التغريدة: {tweet.text}. لا تستخدم هاشتاقات."
                    content = self.generate_content(prompt, model="openai/gpt-4o-mini")
                    
                    if content:
                        # الرد عبر V1.1 (المفتاح السحري لحل 401 في الردود)
                        self.api_v1.update_status(
                            status=content[:280],
                            in_reply_to_status_id=tweet.id,
                            auto_populate_reply_metadata=True
                        )
                        self.state["replied_to"].append(tweet.id)
                        logging.info(f"✅ Target Reply Success: {tweet.id}")
                        break # رد واحد لضمان الجودة
        except Exception as e:
            logging.error(f"❌ Target Reply Error: {e}")

    def handle_rotation_post(self):
        """نشر تدويري باستخدام V2"""
        try:
            kind = self.rotation_kinds[self.state["rotation_idx"] % len(self.rotation_kinds)]
            self.state["rotation_idx"] += 1
            
            prompt = f"اكتب تغريدة احترافية ومشوقة عن ({kind}) بأسلوب تقني عربي ممتع."
            content = self.generate_content(prompt)
            
            if content:
                self.client_v2.create_tweet(text=content[:280])
                logging.info(f"✅ Rotation Post Success: {kind}")
        except Exception as e:
            logging.error(f"❌ Rotation Post Error: {e}")

    def run(self):
        self.handle_targeting_replies()
        time.sleep(20) # فجوة أمان
        self.handle_rotation_post()
        self._save_state()

if __name__ == "__main__":
    TechExpertMasterFinal().run()
