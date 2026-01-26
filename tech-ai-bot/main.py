import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime, timedelta
import random
import time
import hashlib

# ─── إعداد السجل الاحترافي ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgentPro:
    def __init__(self):
        logging.info("=== TechAgent Pro v8.0 [Super Intelligent Mode] ===")
        self.config = self._load_config()

        # ─── إعداد الذكاء الاصطناعي (Qwen 2.5 72B) ───────────────────────
        router_key = os.getenv("OPENROUTER_API_KEY")
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=router_key or os.getenv("OPENAI_API_KEY")
        )
        self.model = "qwen/qwen-2.5-72b-instruct" if router_key else "gpt-4o-mini"

        # ─── إعداد منصة X ──────────────────────────────────────────
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def _load_config(self):
        return {"min_followers": 30, "max_replies_per_run": 5}

    def _generate_smart_content(self, system_prompt, user_input):
        """توليد محتوى فائق الذكاء"""
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.8, # لزيادة الإبداع في الردود
                max_tokens=300
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            return None

    def _process_mentions(self):
        """الرد الذكي جداً على المتابعين"""
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(
                id=me.id, 
                max_results=10, 
                expansions=["author_id", "referenced_tweets.id"],
                tweet_fields=["text", "public_metrics"]
            )
            
            if not mentions.data:
                logging.info("لا توجد تفاعلات جديدة حالياً.")
                return

            # نظام الرد الذكي
            system_instruction = """أنت خبير تقني عبقري، ردودك ذكية، مختصرة، ومثيرة للإعجاب بالعربية الفصحى.
            - إذا كان السؤال تقنياً: أجب بعمق وبصيرة.
            - إذا كان مزاحاً: رد بروح دعابة تقنية راقية.
            - إذا كان نقداً: كن ديبلوماسياً وذكياً.
            - لا تستخدم أكثر من 240 حرفاً."""

            for tweet in mentions.data:
                logging.info(f"تحليل منشن من ID: {tweet.author_id}")
                
                reply_text = self._generate_smart_content(system_instruction, tweet.text)
                
                if reply_text:
                    self.x_client.create_tweet(
                        text=reply_text,
                        in_reply_to_tweet_id=tweet.id
                    )
                    logging.info(f"✅ تم الرد بذكاء على: {tweet.text[:30]}...")
                    time.sleep(random.randint(20, 40)) # حماية من الحظر
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def _publish_leak_tweet(self):
        """نشر تسريبات وسبق صحفي"""
        system_instruction = "أنت رادار التسريبات التقنية العالمي لعام 2026."
        user_prompt = "أعطني سبقاً صحفياً تقنياً واحداً عن Apple أو Nvidia، مكتوباً بأسلوب مشوق جداً وذكي."
        
        content = self._generate_smart_content(system_instruction, user_prompt)
        
        if content:
            # التحقق من عدم التكرار (Hash System)
            current_hash = hashlib.md5(content.encode()).hexdigest()
            is_duplicate = False
            if os.path.exists(LAST_TWEET_FILE):
                with open(LAST_TWEET_FILE, "r") as f:
                    if current_hash in f.read(): is_duplicate = True

            if not is_duplicate:
                self.x_client.create_tweet(text=content)
                with open(LAST_TWEET_FILE, "a") as f:
                    f.write(f"{current_hash}|{datetime.now().isoformat()}\n")
                logging.info("🚀 تم نشر السبق الصحفي الجديد.")

    def run(self):
        try:
            # تنفيذ الردود أولاً ثم النشر
            self._process_mentions()
            self._publish_leak_tweet()
        except Exception as e:
            logging.critical(f"Critical Failure: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
