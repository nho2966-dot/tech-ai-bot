import os
import logging
import tweepy
from openai import OpenAI
from datetime import datetime
import random
import time
import hashlib

# إعداد السجل التقني
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-5s | %(message)s')

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgent:
    def __init__(self):
        logging.info("=== TechAgent Pro v15.0 [Rate-Limit Optimized] ===")
        
        # إعداد AI
        router_key = os.getenv("OPENROUTER_API_KEY")
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1" if router_key else None,
            api_key=router_key or os.getenv("OPENAI_API_KEY")
        )
        self.model = "qwen/qwen-2.5-72b-instruct" if router_key else "gpt-4o-mini"
        
        # إعداد X - تفعيل wait_on_rate_limit للتعامل مع القيود
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False # نجعله False لنتحكم فيه برمجياً ولا يعلق الأكشن
        )

        self.system_instr = (
            "اسمك TechAgent. وكيل تقني مختص. المصادر: TechCrunch, Wired, The Verge. "
            "القواعد: لغة تقنية جافة، جداول Markdown، روابط، والتوقيع +#."
        )

    def _generate_content(self, user_msg):
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": user_msg}],
                temperature=0.2
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _publish_daily(self):
        """نشر المحتوى اليومي - الأولوية القصوى"""
        try:
            tasks = [
                "حلل ثغرة أمنية حديثة مع الرابط.",
                "مقارنة بجدول Markdown بين iPhone 17 و Samsung S25.",
                "آخر تحديثات AI في التعليم 2026."
            ]
            content = self._generate_content(random.choice(tasks))
            if content and len(content) <= 280:
                if "+#" not in content: content += "\n+#"
                self.x_client.create_tweet(text=content)
                logging.info("🚀 تم نشر التغريدة بنجاح.")
                return True
        except tweepy.TooManyRequests:
            logging.warning("⚠️ تجاوز حد الطلبات في النشر (Rate Limit).")
        except Exception as e:
            logging.error(f"X Post Error: {e}")
        return False

    def _process_mentions(self):
        """الرد على المنشنات - مع معالجة حذر للـ Rate Limit"""
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, max_results=5)
            if not mentions.data: return

            for tweet in mentions.data:
                reply = self._generate_content(f"رد تقني جاف على: {tweet.text}")
                if reply:
                    if "+#" not in reply: reply += "\n+#"
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    logging.info(f"✅ تم الرد على المنشن.")
                    time.sleep(5) # تأخير بسيط
        except tweepy.TooManyRequests:
            logging.warning("⚠️ تجاوز حد الطلبات في المنشنات. سأتوقف الآن.")
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def run(self):
        # 1. حاول النشر أولاً (لأن حدوده في الحساب المجاني أضيق)
        self._publish_daily()
        # 2. حاول الرد على المنشنات ثانياً
        self._process_mentions()

if __name__ == "__main__":
    TechAgent().run()
