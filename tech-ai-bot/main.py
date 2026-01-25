import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعداد اللوج لمتابعة الأداء
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TechAgent-Pro-Global] - %(levelname)s - %(message)s'
)

class TechAgentProGlobal:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = self._load_config()
        self.x_client = self._init_x_client()
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = self.config.get('api', {}).get('openai', {}).get('model', 'gpt-4o')
        
    def _load_config(self):
        # البحث عن الملف في نفس مجلد السكريبت لضمان الاستقرار
        config_path = os.path.join(self.base_dir, "config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _init_x_client(self):
        return tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def _generate_response(self, user_input, author):
        """تطبيق القواعد السبعة: مقارنات، لغات، خصوصية، مصادر، محتوى بصري"""
        system_instructions = f"""
        أنت TechAgent Pro Global. التزم بالقواعد التالية حرفياً:
        1. اكتشف لغة السائل (عربي، إنجليزي، فرنسي، إسباني) ورد بها.
        2. عند المقارنة، أنشئ جدول Markdown فوراً 📊.
        3. ارفض طلب أي بيانات شخصية (Privacy First).
        4. استشهد بالمصادر: {self.config['sources']['trusted_domains']}. 
        5. إذا لم تجد معلومة مؤكدة، قل: "لا توجد معلومات موثوقة حديثة من المصادر المعتمدة".
        6. هيكل الرد: ترحيب قصير -> التحليل (جدول إن وجد) -> المصدر -> سؤال متابعة ذكي.
        7. صف صوراً توضيحية (مثل: 🖼️ صورة iPhone 17) لتعزيز الرد.
        """
        
        try:
            response = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"المستخدم @{author} يسأل: {user_input}"}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            return None

    def post_status(self):
        """نشر تغريدة إثبات وجود غنية بالمحتوى"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"🚀 نظام TechAgent Pro Global يعمل بكامل طاقته.\n\n📊 جداول مقارنة دقيقة\n🌍 دعم لغات تلقائي\n🛡️ خصوصية مطلقة\n\nتاريخ التشغيل: {now}\n#TechNews #AI"
        try:
            self.x_client.create_tweet(text=msg)
            logging.info("Status tweet posted successfully.")
        except Exception as e:
            logging.error(f"Failed to post status: {e}")

    def process_mentions(self):
        """الرد على الجميع دون شروط متابعين"""
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(
                id=me.id, 
                expansions=['author_id'], 
                user_fields=['username']
            )
            
            if not mentions.data:
                logging.info("No mentions found.")
                return

            users = {u['id']: u.username for u in mentions.includes['users']}

            for tweet in mentions.data:
                author_username = users.get(tweet.author_id)
                logging.info(f"Answering @{author_username}")
                
                reply = self._generate_response(tweet.text, author_username)
                if reply:
                    # تقسيم الرد إذا تجاوز حد تويتر
                    self.x_client.create_tweet(
                        text=reply[:280], 
                        in_reply_to_tweet_id=tweet.id
                    )
        except Exception as e:
            logging.error(f"Runtime Error: {e}")

if __name__ == "__main__":
    agent = TechAgentProGlobal()
    # تنفيذ المهام
    agent.post_status()
    agent.process_mentions()
