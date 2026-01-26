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
        logging.info("=== TechAgent Pro v23.0 [Multi-Tasking Intelligence] ===")
        
        # إعداد AI و X (Premium Support)
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

        # الدستور الموسع (الاستهداف + الردود + القيمة المضافة)
        self.system_instr = (
            "اسمك TechAgent. أنت وكيل استراتيجي لجمهور الشباب والتقنيين على X. "
            "مهمتك: النشر الاستهدافي والردود الذكية. "
            "المحتوى المسموح: (1) تحليل AI وأدوات العمل الحر، (2) عتاد الألعاب، (3) تسريبات الأجهزة، (4) تصحيح إشاعات تقنية. "
            "الهيكل: ابدأ بملخص مركز، استخدم جداول Markdown للمقارنات، أضف فقرة 'لماذا يهمك هذا؟' للمستقبل، اذكر المصادر الموثوقة. "
            "القواعد: لغة تقنية جافة، موضوعية، بدون لمسات أدبية، والختم دائماً بـ +#."
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
        """الردود الذكية: التفاعل مع المتابعين واستفساراتهم"""
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, max_results=10)
            if not mentions.data: return

            for tweet in mentions.data:
                prompt = f"المتابع يسأل: '{tweet.text}'. أجب تقنياً بجدول أو نقاط وروابط موثوقة. إذا كان السؤال عاماً اقترح أسئلة محددة."
                reply = self._generate_content(prompt, max_tokens=800)
                if reply:
                    if "+#" not in reply: reply += "\n+#"
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    time.sleep(2)
            logging.info("✅ تم الانتهاء من الردود الذكية.")
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def _publish_high_value_post(self):
        """النشر الاستهدافي: تنويع المحتوى بين الفرص والتحليلات"""
        scenarios = [
            "انشر عن أداة AI جديدة تساعد الشباب في الربح من العمل الحر (Freelancing) مع شرح فني ورابط.",
            "مقارنة تقنية بجدول Markdown بين iPhone 17 و Samsung S25 وتحليل أداء المعالجات 2026.",
            "تصحيح إشاعة تقنية منتشرة (Myth Buster) مدعومة بالحقائق والمصادر الرسمية.",
            "تحليل لعتاد ألعاب جديد (GPU
