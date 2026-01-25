import os
import yaml
import logging
import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechAgentPro:
    def __init__(self):
        self.config = self._ultra_smart_search()
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _ultra_smart_search(self):
        """البحث في كل مكان ممكن داخل المستودع عن ملف الإعدادات"""
        target = "config.yaml"
        # 1. البحث في مجلد العمل الحالي
        for root, dirs, files in os.walk(os.getcwd()):
            if target in files:
                config_path = os.path.join(root, target)
                logging.info(f"✅ تم العثور على الملف في: {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        
        # 2. إذا فشل، البحث في المجلد الأب (لحل مشكلة التكرار)
        parent_dir = os.path.dirname(os.getcwd())
        for root, dirs, files in os.walk(parent_dir):
            if target in files:
                config_path = os.path.join(root, target)
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)

        raise FileNotFoundError("❌ تعذر العثور على config.yaml في أي مكان داخل المستودع!")

    def _generate_response(self, text, user):
        # تطبيق القواعد السبعة
        system_prompt = f"""
        أنت TechAgent Pro Global.
        1. اللغة: رد بلغة السائل {user}.
        2. المقارنات: استخدم جداول Markdown 📊.
        3. الخصوصية: ارفض البيانات الشخصية.
        4. المصادر: {self.config.get('sources', {}).get('trusted_domains', [])}.
        5. الغياب: قل 'لا توجد معلومات موثوقة حديثة' إذا لزم الأمر.
        6. الهيكل: ترحيب -> تحليل -> مصدر -> سؤال متابعة.
        7. البصريات: استخدم إيموجي (📊, 🖼️, 🚀) لوصف الصور.
        """
        response = self.ai_client.chat.completions.create(
            model=self.config.get('api', {}).get('openai', {}).get('model', 'gpt-4o'),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"Connected as @{me.username}")
            # نشر إثبات التشغيل
            self.x_client.create_tweet(text="🚀 نظام TechAgent Pro متصل الآن وبكامل طاقته التحليلية 📊.")
            
            # فحص الردود
            mentions = self.x_client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
            if mentions.data:
                users = {u['id']: u.username for u in mentions.includes['users']}
                for tweet in mentions.data:
                    reply = self._generate_response(tweet.text, users.get(tweet.author_id))
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
        except Exception as e:
            logging.error(f"Runtime Error: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
