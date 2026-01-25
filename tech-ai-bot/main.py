import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعدادات اللوج الاحترافية
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TechAgent-Pro-Global] - %(levelname)s - %(message)s'
)

class TechAgentProGlobal:
    def __init__(self):
        self.config = self._load_config()
        self.x_client = self._init_x_client()
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = self.config.get('api', {}).get('openai', {}).get('model', 'gpt-4o')
        
        # إحصائيات الجلسة الداخلية (نظام التحليل)
        self.session_stats = {"replies": 0, "topics": {}}

    def _load_config(self):
        with open("config.yaml", 'r', encoding='utf-8') as f:
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

    def _generate_advanced_response(self, user_input, author):
        """توليد رد يلتزم بالقواعد السبعة الجديدة"""
        system_instructions = f"""
        أنت TechAgent Pro Global. التزم بالقواعد التالية 100%:
        1. اللغة: اكتشف لغة {author} وتحدث بها تلقائياً.
        2. المقارنات: استخدم جداول Markdown والمقارنات الرقمية.
        3. المصادر: استشهد بـ {self.config['sources']['trusted_domains']}. إذا لم تجد مصدر، قل: "لا توجد معلومات موثوقة حديثة".
        4. الخصوصية: ارفض أي طلب لبيانات شخصية فوراً.
        5. الهيكل: ترحيب -> تحليل (جدول/نص) -> مصدر -> سؤال متابعة ذكي.
        6. الأسلوب: مهني، موضوعي، استخدام محدود للإيموجي (📊, 🖼️, 🚀).
        7. الصور: صف المحتوى البصري الذي سيتم البحث عنه (iPhone, Log, etc).
        """
        
        try:
            response = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def post_activation_tweet(self):
        """نشر تغريدة ترحيبية غنية عند التشغيل"""
        msg = "🚀 TechAgent Pro Global متصل الآن.\n\nتحليل تقني دقيق، مقارنات بيانية 📊، ودعم متعدد اللغات 🌍 بناءً على مصادر موثوقة 100%.\n\nتفضل بسؤالك التقني أدناه!"
        try:
            self.x_client.create_tweet(text=msg)
            logging.info("Initial tweet posted.")
        except Exception as e:
            logging.error(f"Failed to post initial tweet: {e}")

    def run(self):
        """المحرك الرئيسي لفحص المنشنات والرد"""
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
            
            if not mentions.data:
                logging.info("No new mentions.")
                return

            users = {u['id']: u.username for u in mentions.includes['users']}

            for tweet in mentions.data:
                author_username = users.get(tweet.author_id)
                logging.info(f"Processing mention from @{author_username}")
                
                reply = self._generate_advanced_response(tweet.text, author_username)
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    self.session_stats["replies"] += 1
                    logging.info(f"Replied to @{author_username}")

        except Exception as e:
            logging.error(f"Runtime error: {e}")

if __name__ == "__main__":
    agent = TechAgentProGlobal()
    # نشر التغريدة الترحيبية (اختياري عند كل تشغيل)
    agent.post_activation_tweet()
    # معالجة الطلبات
    agent.run()
