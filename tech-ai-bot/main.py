import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechAgentPro:
    def __init__(self):
        # تحديد المسار المطلق للمجلد الذي يحتوي على هذا الملف (main.py)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = self._load_config()

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _load_config(self):
        config_path = os.path.join(self.script_dir, "config.yaml")
        if not os.path.exists(config_path):
            logging.error(f"❌ الملف غير موجود في: {config_path}")
            # محاولة البحث في المجلد الرئيسي إذا فشل
            config_path = os.path.join(os.getcwd(), "config.yaml")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _generate_response(self, text, user):
        system_prompt = f"""
        أنت TechAgent Pro Global. التزم بالقواعد الـ 7:
        1. اكتشف لغة {user} ورد بها (عربي، إنجليزي، إلخ).
        2. للمقارنات: استخدم جداول Markdown 📊.
        3. ارفض طلب البيانات الشخصية (Privacy Rules).
        4. المصادر المعتمدة: {self.config['sources']['trusted_domains']}.
        5. إذا لم تجد مصدر موثوق حديث: استخدم جملة الـ fallback المحددة في الإعدادات.
        6. الهيكل: ترحيب -> تحليل وبحث -> مصدر -> سؤال متابعة ذكي.
        7. استخدم إيموجي للتوجيه البصري (📊, 🖼️, 🚀).
        """
        response = self.ai_client.chat.completions.create(
            model=self.config['api']['openai'].get('model', 'gpt-4o'),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"Connected as @{me.username}")
            
            # 1. إثبات التواجد
            self.x_client.create_tweet(text="🚀 TechAgent Pro Global متصل.\nنظام التحليل التقني والمقارنات البيانية جاهز الآن 📊.")
            
            # 2. فحص والرد على المنشنات
            mentions = self.x_client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
            if mentions.data:
                users = {u['id']: u.username for u in mentions.includes['users']}
                for tweet in mentions.data:
                    author = users.get(tweet.author_id)
                    logging.info(f"Processing mention from @{author}")
                    reply = self._generate_response(tweet.text, author)
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
            
        except Exception as e:
            logging.error(f"Runtime Error: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
