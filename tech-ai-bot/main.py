import os
import logging
import tweepy
from openai import OpenAI
import random
import time

# إعداد السجل بنبرة احترافية
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgent:
    def __init__(self):
        logging.info("=== TechAgent Pro v26.0 [Optimized for X Premium] ===")
        
        # إعداد AI
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        # إعداد X - تعطيل الانتظار التلقائي للتحكم اليدوي
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=False 
        )

        # الهوية المعتمدة
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
        """معالجة الردود بذكاء وحذر"""
        try:
            # لجلب المنشنات نحتاج ID الحساب. بدلاً من طلب get_me() دائماً
            # سنحاول جلبه مرة واحدة، وفي حال الفشل نعتمد على النشر فقط
            me = self.x_client.get_me()
            if not me.data: return
            
            # طلب 5 منشنات فقط لتوفير الكوتا
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions.data: 
                logging.info("ℹ️ لا توجد منشنات جديدة للرد عليها.")
                return

            for tweet in mentions.data:
                reply = self._generate_content(f"رد تقني جاف ومفيد على: {tweet.text}")
                if reply:
                    if "+#" not in reply: reply += "\n+#"
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    logging.info(f"✅ تم الرد على: {tweet.id}")
                    time.sleep(5) # فاصل زمني بسيط بين الردود
        except tweepy.TooManyRequests:
            logging.warning("⚠️ تم بلوغ حد الطلبات للمنشنات. سيتم التخطي.")
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def _publish_post(self):
        """النشر الاستهدافي للشباب"""
        try:
            tasks = ["أداة AI للعمل الحر", "مقارنة مواصفات هواتف 2026", "تسريب عتاد ألعاب"]
            content = self._generate_content(random.choice(tasks))
            if content:
                if "+#" not in content: content += "\n+#"
                self.x_client.create_tweet(text=content)
                logging.info("🚀 تم النشر الاستهدافي بنجاح.")
        except tweepy.TooManyRequests:
            logging.warning("⚠️ تم بلوغ حد الطلبات للنشر.")
        except Exception as e:
            logging.error(f"Post Error: {e}")

    def run(self):
        # النشر أولاً لأنه الأهم للأداء العام، ثم محاولة الردود
        self._publish_post()
        self._process_mentions()

if __name__ == "__main__":
    TechAgent().run()
