import os
import logging
import tweepy
from openai import OpenAI
from datetime import datetime
import random
import time
import hashlib

# إعداد السجل بنبرة احترافية
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgent:
    def __init__(self):
        logging.info("=== TechAgent Pro v24.0 [Final Verified Version] ===")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        self.system_instr = (
            "اسمك TechAgent. أنت وكيل استراتيجي لجيل الشباب على X. "
            "مهمتك: النشر الاستهدافي والردود الذكية. "
            "المحتوى: (1) أدوات العمل الحر و AI، (2) عتاد الألعاب، (3) تسريبات الأجهزة، (4) تصحيح إشاعات تقنية. "
            "الهيكل: ملخص مركز، جداول Markdown للمقارنات، فقرة 'لماذا يهمك هذا؟'، وروابط موثوقة. "
            "القواعد: لغة تقنية جافة، موضوعية، بدون لمسات لغوية، والختم بـ +#."
        )

    def _generate_content(self, task_prompt, max_tokens=1500):
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": self.system_instr},
                    {"role": "user", "content": task_prompt}
                ],
                temperature=0.2,
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _process_mentions(self):
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, max_results=10)
            if not mentions.data: return

            for tweet in mentions.data:
                prompt = f"أجب تقنياً ومباشرة على استفسار المتابع: '{tweet.text}'."
                reply = self._generate_content(prompt, max_tokens=800)
                if reply:
                    if "+#" not in reply: reply += "\n+#"
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    time.sleep(2)
            logging.info("✅ تم إنهاء معالجة الردود.")
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def _publish_daily_scoop(self):
        scenarios = [
            "انشر عن أداة AI جديدة تخدم العمل الحر للشباب مع شرح فني ورابط.",
            "مقارنة بجدول Markdown بين iPhone 17 و Samsung S25 بناءً على التسريبات.",
            "تصحيح إشاعة تقنية منتشرة (Myth Buster) بالحقائق والمصادر.",
            "تحليل لعتاد ألعاب جديد (GPU) وأثره على الأداء التقني."
        ]
        selected = random.choice(scenarios)
        content = self._generate_content(selected)
        
        if content:
            if "+#" not in content: content += "\n+#"
            try:
                self.x_client.create_tweet(text=content)
                logging.info("🚀 تم النشر الاستهدافي بنجاح.")
            except Exception as e:
                logging.error(f"Post Error: {e}")

    def run(self):
        self._process_mentions()
        self._publish_daily_scoop()

if __name__ == "__main__":
    TechAgent().run()
