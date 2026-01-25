import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# ─── إعداد السجل (logging) ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

class TechAgentPro:
    def __init__(self):
        # معلومات تشخيصية أساسية
        logging.info("بدء تشغيل TechAgent Pro")
        logging.info(f"المسار الحالي: {os.getcwd()}")
        logging.info(f"GITHUB_WORKSPACE: {os.getenv('GITHUB_WORKSPACE')}")
        logging.info(f"الملفات في المجلد الحالي: {os.listdir('.')[:15]}")

        # تحميل التكوين
        self.config = self._load_config()

        # التحقق من مفاتيح X
        required_x_keys = [
            "X_BEARER_TOKEN", "X_API_KEY", "X_API_SECRET",
            "X_ACCESS_TOKEN", "X_ACCESS_SECRET"
        ]
        missing_keys = [k for k in required_x_keys if not os.getenv(k)]
        if missing_keys:
            raise ValueError(f"مفاتيح X مفقودة: {', '.join(missing_keys)}")

        # اتصال X
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY مفقود في Secrets")
        self.ai_client = OpenAI(api_key=api_key)
        self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")

    def _load_config(self):
        """تحميل التكوين – الأولوية: Secret → ملف → افتراضي"""
        # 1. GitHub Secret (الأولوية الأولى)
        secret_yaml = os.getenv("CONFIG_YAML")
        if secret_yaml:
            logging.info("تم تحميل التكوين من GitHub Secret → CONFIG_YAML")
            try:
                return yaml.safe_load(secret_yaml)
            except Exception as e:
                logging.error(f"فشل تحليل Secret YAML: {e}")

        # 2. البحث عن ملف config.yaml (للتطوير المحلي)
        target = "config.yaml"
        base_dir = os.getenv("GITHUB_WORKSPACE", os.getcwd())
        logging.info(f"البحث عن {target} في: {base_dir}")

        for root, _, files in os.walk(base_dir):
            if target in files:
                path = os.path.join(root, target)
                logging.info(f"تم العثور على الملف: {path}")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logging.error(f"خطأ قراءة {path}: {e}")

        # 3. إعدادات افتراضية آمنة
        logging.warning("استخدام إعدادات افتراضية – لا config متاح")
        return {
            "api": {"openai": {"model": "gpt-4o-mini"}},
            "sources": {
                "trusted_domains": [
                    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
                    "cnet.com", "engadget.com", "bloomberg.com", "reuters.com"
                ]
            },
            "behavior": {"max_replies_per_hour": 10}
        }

    def _generate_response(self, tweet_text: str, username: str) -> str:
        """توليد رد احترافي وفق القواعد"""
        trusted_domains = self.config.get("sources", {}).get("trusted_domains", [])

        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني محايد ومهني.
        القواعد الصارمة:
        1. الرد بلغة التغريدة الغالبة (غالباً عربي أو إنجليزي).
        2. لا تقدم معلومة تقنية إلا مدعومة بمصدر موثوق من: {', '.join(trusted_domains)}
        3. إذا لم يكن هناك مصدر موثوق → قل: 'لا توجد معلومات موثوقة حديثة متاحة حالياً'
        4. الرد أقل من 280 حرف، مهني، يفتح نقاشاً ذكياً، ينتهي بسؤال متابعة.
        5. لا تطلب أي بيانات شخصية أو خاصة بالمطور.
        """

        user_message = f"@{
