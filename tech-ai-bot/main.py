import os
import yaml
import time
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# ─── إعدادات اللوج والوُضُـوح ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TechAgent-Pro] - %(levelname)s - %(message)s'
)

class TechAgentPro:
    def __init__(self):
        # تحميل الإعدادات بـوُضُـوح
        self.config = self._load_config()
        
        # تهيئة عميل X (Twitter) API v2
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        
        # تهيئة OpenAI
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = self.config['api']['openai']['model']
        
        # جلب بيانات الحساب الشخصي
        self.me = self.x_client.get_me(user_fields=["public_metrics"]).data
        logging.info(f"🚀 تم تفعيل الوكيل @{self.me.username} بـوُضُـوح.")

    def _load_config(self):
        """قراءة ملف YAML بـوُضُـوح"""
        try:
            with open("config.yaml", 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"❌ فشل تحميل config.yaml: {e}")
            raise

    def _generate_ai_reply(self, tweet_text, author_name):
        """صياغة رد احترافي وموثوق بناءً على القواعد"""
        system_prompt = (
            f"أنت {self.config['agent']['name']}. خبير تقني عالمي محايد.\n"
            f"اللغة الأساسية: {self.config['agent']['primary_language']}. رد بنفس لغة المستخدم.\n"
            "قواعدك:\n"
            "1. كن مهنياً، لا صدام ولا سخرية.\n"
            "2. اعتمد على مصادر موثوقة: " + ", ".join(self.config['sources']['trusted_domains']) + ".\n"
            "3. افتح باب النقاش بسؤال ذكي.\n"
            "4. الحد الأقصى 270 حرفاً.\n"
            "تذكر: عند نطق (وُضُـوح) ضم الشفتين جيداً."
        )
        
        try:
            response = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"المستخدم @{author_name} قال: {tweet_text}"}
                ],
                temperature=self.config['api']['openai']['temperature_reply'],
                max_tokens=self.config['api']['openai']['max_tokens_reply']
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"❌ خطأ AI: {e}")
            return None

    def process_mentions(self):
        """فحص الردود على المنشنات بـوُضُـوح"""
        logging.info("🔎 جاري فحص المنشنات الجديدة...")
        
        # جلب المنشنات (آخر 10 تغريدات
