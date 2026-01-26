import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime
import random
import time

# ─── إعداد السجل ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

class TechAgentPro:
    def __init__(self):
        logging.info("=== تشغيل TechAgent Pro v3: محتوى حقيقي 📊 ===")

        # ─── اتصال الذكاء الاصطناعي ─────────────────────────────────────
        openai_key = os.getenv("OPENAI_API_KEY")
        self.ai_client = OpenAI(api_key=openai_key)
        self.model = "gpt-4o-mini"

        # ─── اتصال X (API v2) ───────────────────────────────────────────
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        me = self.x_client.get_me().data
        self.my_id = me.id
        self.my_username = me.username.lower()

    def _generate_content(self):
        """إنشاء تغريدة تقنية حقيقية لإفادة المتابعين"""
        prompt = "اكتب تغريدة تقنية مفيدة جداً بالعربية عن (الذكاء الاصطناعي أو الهواتف). استخدم إيموجي وهاشتاق. الرد < 270 حرف."
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250
            )
            return resp.choices[0].message.content.strip()
        except Exception: return None

    def _generate_reply(self, tweet_text, username):
        """توليد رد تقني محترف بجدول مقارنة إذا لزم الأمر"""
        prompt = f"حلل تقنياً: '{tweet_text}'. رد على @{username} بجدول مقارنة صغير 📊 أو معلومة دقيقة. الرد < 260 حرف."
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return resp.choices[0].message.content.strip()
        except Exception: return None

    def run(self):
        try:
            # 1. نشر التغريدة التقنية اليومية (محتوى حقيقي)
            content = self._generate_content()
            if content:
                self.x_client.create_tweet(text=content)
                logging.info(f"✨ تم نشر محتوى تقني جديد: {content[:50]}...")
                time.sleep(60) # انتظار دقيقة قبل البدء بالمنشنات

            # 2. معالجة المنشنات
            mentions = self.x_client.get_users_mentions(
                id=self.my_id,
                expansions=["author_id"],
                user_fields=["username"]
            )

            if mentions.data:
                users_map = {u.id: u.username for u in mentions.includes.get("users", [])}
                for tweet in mentions.data:
                    author = users_map.get(tweet.author_id)
                    if not author or author.lower() == self.my_username: continue

                    logging.info(f"📩 معالجة منشن من @{author}")
                    reply_text = self._generate_reply(tweet.text, author)
                    
                    if reply_text:
                        # التأكد من أن الرد يبدأ بالمنشن لضمان ظهوره في "Replies"
                        final_reply = f"@{author} {reply_text}" if not reply_text.startswith("@") else reply_text
                        self.x_client.create_tweet(
                            text=final_reply[:280],
                            in_reply_to_tweet_id=tweet.id
                        )
                        logging.info(f"✅ تم الرد على @{author}")
                        time.sleep(random.randint(30, 90)) # تأخير عشوائي طبيعي

        except Exception as e:
            logging.error(f"خطأ: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
