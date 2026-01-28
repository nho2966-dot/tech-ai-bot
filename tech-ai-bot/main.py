import os
import json
import time
import random
import logging
import tweepy
from openai import OpenAI

# إعداد المسارات الأساسية
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO, format="%(message)s")

# أنواع المحتوى للتدوير (بناءً على هيكلك)
ROTATION_KINDS = ["breaking_news", "ai_daily_life", "ai_tool"]

class TechExpertProPremium:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Premium Logic v88.6] ---")
        
        # 1. إعداد OpenAI/OpenRouter
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1", 
            api_key=os.environ["OPENROUTER_API_KEY"]
        )
        
        # 2. إعداد X Client (استخدام المفاتيح الأربعة المحدثة)
        self.client_v2 = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_SECRET"],
            wait_on_rate_limit=True
        )
        
        # تحميل حالة البوت
        self.state = self._load_state()

    def _load_state(self):
        """تحميل الحالة والتأكد من وجود المفاتيح المطلوبة"""
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
        """حفظ الحالة في ملف JSON"""
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def handle_smart_replies(self):
        """استهداف التغريدات والرد عليها بذكاء (Targeting)"""
        try:
            # التحقق من الهوية أولاً (لحل مشكلة الـ 401)
            me = self.client_v2.get_me()
            my_id = me.data.id
            logging.info(f"Authenticated as: @{me.data.username}")

            # البحث عن تغريدات تقنية عربية
            query = "(برمجة OR تقنية OR ذكاء_اصطناعي) lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    # عدم الرد على النفس أو تغريدات تم الرد عليها
                    if tweet.author_id == my_id: continue
                    if tweet.id in self.state["replied_to"]: continue

                    # توليد رد ذكي عبر AI
                    res = self.ai_client.chat.completions.create(
                        model="openai/gpt-4o-mini",
                        messages=[{"role": "user", "content": f"اكتب رداً تقنياً ذكياً ومفيداً جداً باللغة العربية (بدون هاشتاقات) على هذه التغريدة: {tweet.text}"}]
                    )
                    reply_text = res.choices[0].message.content.strip()

                    # إرسال الرد
                    self.client_v2.create_tweet(
                        text=reply_text[:280],
                        in_reply_to_tweet_id=tweet.id
                    )
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"✅ Replied successfully to tweet {tweet.id}")
                    break # رد واحد في كل دورة لتجنب السبام
            else:
                logging.info("No relevant tweets found for targeting.")
        except Exception as e:
            logging.error(f"❌ Smart Reply Logic Error: {e}")

    def execute_rotation_post(self):
        """نشر محتوى متنوع بناءً على التدوير (Rotation)"""
        try:
            kind = ROTATION_KINDS[self.state["rotation_idx"] % len(ROTATION_KINDS)]
            self.state["rotation_idx"] += 1
            
            # توليد المحتوى بناءً على النوع
            prompt = f"اكتب تغريدة احترافية ومثيرة للاهتمام عن ({kind}) باللغة العربية لمجتمع التقنية."
            res = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": prompt}]
            )
            tweet_body = res.choices[0].message.content.strip()

            # النشر على X
            self.client_v2.create_tweet(text=tweet_body[:280])
            logging.info(f"✅ Successfully posted {kind} tweet.")
        except Exception as e:
            logging.error(f"❌ Posting Error: {e}")

    def run(self):
        """بدء العمليات"""
        self.handle_smart_replies() # أولاً: الردود الذكية
        time.sleep(10) # انتظار بسيط
        self.execute_rotation_post() # ثانياً: النشر التدويري
        self._save_state() # ثالثاً: حفظ الحالة

if __name__ == "__main__":
    TechExpertProPremium().run()
