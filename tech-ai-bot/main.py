import os
import logging
import tweepy
from openai import OpenAI
import random
import time

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgent:
    def __init__(self):
        logging.info("=== TechAgent Pro v25.0 [Rate-Limit Resilience] ===")
        
        # إعداد AI
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        # إعداد X - تعطيل الانتظار التلقائي لتجنب تعليق الـ Action
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False 
        )

        self.system_instr = (
            "اسمك TechAgent. وكيل تقني لجيل الشباب. لغة جافة، جداول Markdown، روابط، والختم بـ +#."
        )

    def _generate_content(self, prompt):
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
                temperature=0.2
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _process_mentions(self):
        """معالجة الردود مع حماية ضد الـ Rate Limit"""
        try:
            # محاولة جلب المعرف الخاص بي
            me = self.x_client.get_me()
            if not me.data: return
            
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions.data: return

            for tweet in mentions.data:
                reply = self._generate_content(f"رد تقني جاف على: {tweet.text}")
                if reply:
                    if "+#" not in reply: reply += "\n+#"
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    logging.info(f"✅ تم الرد على المنشن {tweet.id}")
                    time.sleep(5)
        except tweepy.TooManyRequests:
            logging.warning("⚠️ تجاوز حد الطلبات (Rate Limit). سيتم التوقف الآن ومعاودة المحاولة لاحقاً.")
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def _publish_post(self):
        """النشر الاستهدافي"""
        try:
            scenarios = ["أداة AI للعمل الحر", "مقارنة هواتف بجدول", "تحليل عتاد ألعاب"]
            content = self._generate_content(random.choice(scenarios))
            if content:
                if "+#" not in content: content += "\n+#"
                self.x_client.create_tweet(text=content)
                logging.info("🚀 تم النشر بنجاح.")
        except tweepy.TooManyRequests:
            logging.warning("⚠️ حد النشر ممتلئ حالياً.")
        except Exception as e:
            logging.error(f"Post Error: {e}")

    def run(self):
        # تنفيذ النشر أولاً كأولوية، ثم محاولة الردود
        self._publish_post()
        self._process_mentions()

if __name__ == "__main__":
    TechAgent().run()
