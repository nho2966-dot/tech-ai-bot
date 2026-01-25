import os
import yaml
import logging
import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechAgentPro:
    def __init__(self):
        self.config = self._find_and_load_config()
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _find_and_load_config(self):
        """يبحث عن config.yaml في المجلد الحالي وكل المجلدات المحيطة به صعوداً ونزولاً"""
        filename = "config.yaml"
        # البحث في المجلد الحالي وما فوقه
        current_search = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):  # الصعود لـ 5 مستويات
            potential_path = os.path.join(current_search, filename)
            if os.path.exists(potential_path):
                logging.info(f"✅ تم العثور على الإعدادات في: {potential_path}")
                with open(potential_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            current_search = os.path.dirname(current_search)
        
        # إذا لم يجد، يبحث في كامل بيئة العمل (لـ GitHub Actions)
        workspace = os.getenv("GITHUB_WORKSPACE", ".")
        for root, dirs, files in os.walk(workspace):
            if filename in files:
                path = os.path.join(root, filename)
                logging.info(f"✅ تم العثور على الإعدادات عبر البحث الشامل: {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)

        raise FileNotFoundError("❌ فشل العثور على config.yaml في كامل المستودع.")

    def _generate_response(self, text, user):
        # القواعد السبعة الأساسية
        system_prompt = f"""
        أنت TechAgent Pro Global. التزم بالقواعد الـ 7:
        1. اللغة: رد بنفس لغة {user}.
        2. المقارنات: جداول Markdown 📊.
        3. الخصوصية: ارفض أي طلب لبيانات شخصية.
        4. المصادر: {self.config.get('sources', {}).get('trusted_domains', [])}.
        5. عدم توفر معلومة: قل "لا توجد معلومات موثوقة حديثة".
        6. الهيكل: ترحيب -> تحليل -> مصدر -> سؤال متابعة.
        7. الإيموجي: باعتدال (📊, 🖼️, 🚀).
        """
        response = self.ai_client.chat.completions.create(
            model=self.config.get('api', {}).get('openai', {}).get('model', 'gpt-4o'),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()

    def run(self):
        try:
            me = self.x_client.get_me().data
            self.x_client.create_tweet(text="🚀 TechAgent Pro Global متصل الآن.\nجاهز لتحليل طلباتكم التقنية ومقارنتها بدقة 📊.")
            
            mentions = self.x_client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
            if mentions.data:
                users = {u['id']: u.username for u in mentions.includes['users']}
                for tweet in mentions.data:
                    author = users.get(tweet.author_id)
                    reply = self._generate_response(tweet.text, author)
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
        except Exception as e:
            logging.error(f"Error: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
