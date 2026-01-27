import os
import logging
import tweepy
from openai import OpenAI
import random
import time

logging.basicConfig(level=logging.INFO, format='%(message)s')

class TechExpertMaster:
    def __init__(self):
        logging.info("--- Tech Expert Strategic Session [v81.0] ---")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        self.client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # بنك المواضيع الاستهدافية (محتوى v79.0)
        self.trending_categories = {
            "AI": "نماذج Generative AI، الوكلاء الذكيين AI Agents، أدوات ChatGPT وGrok، وجدل الوظائف والأخلاقيات",
            "Security": "هجمات Ransomware، تسريبات البيانات، Zero Trust، واستخدام AI في الدفاع والهجمات",
            "Blockchain": "تحركات Bitcoin، تقنيات Web3، تشريعات الكريبتو، واختراقات المنصات",
            "Cloud": "أخبار AWS وAzure وGoogle Cloud، الأعطال الكبرى، وخدمات السحابة الأمنية",
            "ConsumerTech": "إصدارات Apple وSamsung، تحديثات iOS وAndroid، ومقارنات الأداء الفعلي",
            "Space": "SpaceX وإطلاق الصواريخ، الأقمار الصناعية، وسباق الفضاء التجاري",
            "Connectivity": "توسعة شبكات 5G و6G، تطبيقات IoT، ونقاشات الخصوصية",
            "DevOps": "لغات Python وRust، أدوات AI للمبرمجين، وتغييرات GitHub وOpenAI"
        }

        # تعليمات الهيكلة والأنسنة (محتوى v80.0)
        self.system_instr = (
            "أنت خبير تقني ومؤثر مستقل على X. أسلوبك بشري خبير وذكي. "
            "التزم دائماً بالترتيب المثالي للتغريدة:\n"
            "1- الخطّاف (Hook): سطر أول صادم أو تساؤلي.\n"
            "2- القيمة (Value): شرح تقني مركز وبسيط.\n"
            "3- التوضيح: مثال قصير أو مقارنة (إن وجد).\n"
            "4- التفاعل (CTA): سؤال جدلي للمتابعين.\n"
            "5- الوسوم: 1-3 وسوم تقنية فقط.\n"
            "ممنوع الإشارة لأنك بوت. الختم دائماً بـ +#"
        )

    def _interact(self):
        """نظام الردود الذكية الاستهدافي"""
        logging.info("Checking for mentions...")
        try:
            me = self.client_v2.get_me(user_auth=True).data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5, user_auth=True)
            
            if mentions and mentions.data:
                for tweet in mentions.data:
                    prompt = f"بصفتك خبير تقني بشري، رد بذكاء وجدل مختصر جداً على: {tweet.text}"
                    resp = self.ai_client.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}]
                    )
                    reply = resp.choices[0].message.content.strip()
                    self.client_v2.create_tweet(text=f"{reply}", in_reply_to_tweet_id=tweet.id, user_auth=True)
                    logging.info(f"Replied to: {tweet.id}")
        except Exception as e:
            logging.error(f"Interaction Error: {e}")

    def _post(self):
        """نشر استهدافي يدمج مواضيع الترند بالهيكلة الذهبية"""
        try:
            category_key = random.choice(list(self.trending_categories.keys()))
            details = self.trending_categories[category_key]
            
            prompt = (
                f"اكتب تغريدة استهدافية عن {category_key}. التفاصيل: {details}. "
                "طبق الهيكلة: Hook قوي، Value تقنية، CTA، ووسوم."
            )
            
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}]
            )
            content = resp.choices[0].message.content.strip()
            
            self.client_v2.create_tweet(text=f"{content}\n\n+#", user_auth=True)
            logging.info(f"Published strategic post about {category_key}")
        except Exception as e:
            logging.error(f"Post Error: {e}")

    def run(self):
        self._post()
        time.sleep(20) # فاصل زمني لضمان معالجة البيانات
        self._interact()

if __name__ == "__main__":
    TechExpertMaster().run()
