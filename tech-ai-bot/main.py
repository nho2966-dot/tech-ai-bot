import os
import yaml
import logging
import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechAgentPro:
    def __init__(self):
        # تحميل الإعدادات من نفس المجلد
        base_path = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_path, "config.yaml"), 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _generate_response(self, text, user):
        system_prompt = f"""
        أنت TechAgent Pro Global. التزم بالقواعد الـ 7:
        1. اكتشف لغة {user} ورد بها تلقائياً.
        2. عند المقارنة، استخدم جداول Markdown 📊.
        3. ارفض طلب البيانات الشخصية (الخصوصية أولاً).
        4. المصادر المعتمدة: {self.config['sources']['trusted_domains']}.
        5. إذا لم تجد مصدر، استخدم جملة الـ fallback المحددة.
        6. الهيكل: ترحيب -> تحليل -> مصدر -> سؤال متابعة.
        7. استخدم إيموجي باعتدال (📊, 🖼️, 🚀).
        """
        response = self.ai_client.chat.completions.create(
            model=self.config['api']['openai']['model'],
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()

    def run(self):
        try:
            me = self.x_client.get_me().data
            # نشر تغريدة الحالة
            self.x_client.create_tweet(text="🚀 TechAgent Pro Global متصل الآن وجاهز للتحليل التقني 📊.")
            
            # فحص المنشنات
            mentions = self.x_client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
            if mentions.data:
                users = {u['id']: u.username for u in mentions.includes['users']}
                for tweet in mentions.data:
                    author = users.get(tweet.author_id)
                    reply = self._generate_response(tweet.text, author)
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    logging.info(f"Replied to @{author}")
        except Exception as e:
            logging.error(f"Error: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
