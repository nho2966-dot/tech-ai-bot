import os
import yaml
import logging
import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechAgentPro:
    def __init__(self):
        self.config = self._smart_load_config()
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _smart_load_config(self):
        """يبحث عن config.yaml في المجلد الحالي، ثم المجلدات الأعلى، ثم كامل المستودع"""
        filename = "config.yaml"
        # 1. المجلد الحالي للسكريبت
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        
        if not os.path.exists(path):
            # 2. البحث في المجلد الرئيسي للمشروع (خارج المجلدات المتكررة)
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            path = os.path.join(base_dir, filename)

        if not os.path.exists(path):
            logging.error(f"❌ لم يتم العثور على الإعدادات. جاري محاولة أخيرة...")
            raise FileNotFoundError(f"Config file not found in any expected paths.")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _generate_response(self, text, user):
        system_prompt = f"""
        أنت TechAgent Pro Global. التزم بالقواعد الـ 7:
        1. اكتشف لغة {user} ورد بها. 2. للمقارنات: جداول Markdown 📊. 
        3. ارفض طلب البيانات الشخصية. 4. المصادر: {self.config['sources']['trusted_domains']}. 
        5. إذا لم تجد مصدر: استخدم جملة الـ fallback. 
        6. الهيكل: ترحيب -> تحليل -> مصدر -> سؤال متابعة. 7. إيموجي (📊, 🖼️, 🚀).
        """
        response = self.ai_client.chat.completions.create(
            model=self.config['api']['openai'].get('model', 'gpt-4o'),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"🚀 متصل كـ @{me.username}")
            # تنفيذ المهام: نشر حالة وفحص المنشنات
            self.x_client.create_tweet(text="🚀 TechAgent Pro متصل وجاهز للتحليل التقني 📊.")
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
