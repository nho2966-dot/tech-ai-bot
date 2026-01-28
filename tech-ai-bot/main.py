import os
import json
import time
import random
import logging
import tweepy
from openai import OpenAI

# 1. إعدادات المسارات والسجلات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

# 2. مصفوفة تدوير المحتوى (Rotation)
ROTATION_KINDS = ["breaking_news", "ai_daily_life", "ai_tool"]

class TechExpertPro:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Premium Final Version] ---")
        
        # إعداد عميل الذكاء الاصطناعي (OpenRouter)
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1", 
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        # إعداد عميل X (Twitter v2) باستخدام المفاتيح الأربعة
        self.client_v2 = tweepy.Client(
            consumer_key=os.environ.get("X_API_KEY"),
            consumer_secret=os.environ.get("X_API_SECRET"),
            access_token=os.environ.get("X_ACCESS_TOKEN"),
            access_token_secret=os.environ.get("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        
        self.state = self._load_state()
        self.my_id = None

    def _load_state(self):
        """تحميل حالة البوت من ملف JSON"""
        default_state = {"replied_to": [], "rotation_idx": 0}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in default_state.items():
                        data.setdefault(k, v)
                    return data
            except Exception as e:
                logging.warning(f"Could not load state, using defaults: {e}")
        return default_state

    def _save_state(self):
        """حفظ حالة البوت"""
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving state: {e}")

    def handle_smart_replies(self):
        """نظام الردود الذكية المستهدفة (Targeting)"""
        try:
            # التحقق من تسجيل الدخول وجلب المعرف
            me = self.client_v2.get_me()
            self.my_id = me.data.id
            logging.info(f"Connected as: @{me.data.username}")

            # البحث عن تغريدات تقنية عربية (تبسيط الاستعلام لضمان القبول)
            query = "تقنية OR برمجة lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(
                query=query, 
                max_results=10, # فحص قائمة أكبر لاختيار الأنسب
                tweet_fields=['author_id', 'text']
            )
            
            if tweets.data:
                for tweet in tweets.data:
                    # شروط الرد: ليس أنا، ولم أرد سابقاً
                    if tweet.author_id == self.my_id: continue
                    if tweet.id in self.state["replied_to"]: continue

                    # توليد رد تقني مختصر
                    res = self.ai_client.chat.completions.create(
                        model="openai/gpt-4o-mini",
                        messages=[{"role": "user", "content": f"اكتب رداً تقنياً ذكياً ومختصراً جداً باللغة العربية على: {tweet.text}"}]
                    )
                    reply_text = res.choices[0].message.content.strip()

                    # تنفيذ الرد
                    self.client_v2.create_tweet(
                        text=reply_text[:280],
                        in_reply_to_tweet_id=tweet.id
                    )
                    
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"✅ Successfully replied to tweet {tweet.id}")
                    # نكتفي برد واحد في كل دورة تشغيل لحماية الحساب
                    return 
            else:
                logging.info("No suitable tweets found for replies in this cycle.")
        except Exception as e:
            logging.error(f"❌ Smart Reply Logic Error: {e}")

    def execute_rotation_post(self):
        """نظام النشر التدويري التلقائي (Rotation)"""
        try:
            # اختيار نوع المحتوى بناءً على الترتيب
            kind = ROTATION_KINDS[self.state["rotation_idx"] % len(ROTATION_KINDS)]
            self.state["rotation_idx"] += 1
            
            # توليد المحتوى عبر AI
            prompt = f"اكتب تغريدة تقنية احترافية باللغة العربية عن موضوع: {kind}. اجعلها جذابة للمتابعين."
            res = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": prompt}]
            )
            tweet_content = res.choices[0].message.content.strip()

            # النشر العام
            self.client_v2.create_tweet(text=tweet_content[:280])
            logging.info(f"✅ Successfully posted a {kind} tweet.")
        except Exception as e:
            logging.error(f"❌ Posting Error: {e}")

    def run(self):
        """تشغيل الدورة الكاملة للمهمة"""
        self.handle_smart_replies()
        # فجوة زمنية بسيطة بين الرد والنشر لتبدو كنشاط بشري
        time.sleep(15) 
        self.execute_rotation_post()
        self._save_state()
        logging.info("--- Cycle Completed ---")

if __name__ == "__main__":
    try:
        bot = TechExpertPro()
        bot.run()
    except Exception as e:
        logging.critical(f"Bot failed to start: {e}")
