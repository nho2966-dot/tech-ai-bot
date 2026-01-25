import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# ─── إعداد السجل ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

class TechAgentPro:
    def __init__(self):
        logging.info("بدء تشغيل TechAgent Pro")
        logging.info(f"المسار الحالي: {os.getcwd()}")
        logging.info(f"متغير GITHUB_WORKSPACE: {os.getenv('GITHUB_WORKSPACE')}")
        logging.info(f"الملفات في المجلد الحالي: {os.listdir('.')[:15]}")

        self.config = self._load_config()

        # اتصال X
        required_env = ["X_BEARER_TOKEN", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing = [k for k in required_env if not os.getenv(k)]
        if missing:
            raise ValueError(f"مفاتيح X مفقودة: {', '.join(missing)}")

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
            raise ValueError("OPENAI_API_KEY مفقود")

        self.ai_client = OpenAI(api_key=api_key)
        self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")

    def _load_config(self):
        """تحميل config.yaml بطريقة ذكية"""
        # الأولوية 1: GitHub Secret
        secret_content = os.getenv("CONFIG_YAML")
        if secret_content:
            logging.info("تحميل التكوين من GitHub Secret → CONFIG_YAML")
            try:
                return yaml.safe_load(secret_content)
            except Exception as e:
                logging.error(f"فشل تحليل Secret: {e}")

        # الأولوية 2: ملف في الريبو
        target_file = "config.yaml"
        base_dir = os.getenv("GITHUB_WORKSPACE", os.getcwd())

        for root, _, files in os.walk(base_dir):
            if target_file in files:
                path = os.path.join(root, target_file)
                logging.info(f"تم العثور على config.yaml في: {path}")
                try:
                    with open(path, encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logging.error(f"خطأ قراءة {path}: {e}")

        # الأولوية 3: إعدادات افتراضية آمنة
        logging.warning("استخدام إعدادات افتراضية – لا config.yaml")
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
        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني محايد ومهني.
        القواعد:
        1. الرد بلغة التغريدة الرئيسية (@{username}).
        2. لا معلومات تقنية بدون مصدر موثوق من:
           {', '.join(self.config.get('sources', {}).get('trusted_domains', []))}
        3. إذا لم يكن هناك مصدر → قل: "لا توجد معلومات موثوقة حديثة متاحة حالياً"
        4. الرد < 280 حرف، مهني، ينتهي بسؤال ذكي.
        5. لا تطلب أي بيانات شخصية أبدًا.
        """

        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"@{username} كتب: {tweet_text}\nرد احترافي فقط."}
                ],
                temperature=0.55,
                max_tokens=140
            )
            reply = resp.choices[0].message.content.strip()
            return reply[:277] + "…" if len(reply) > 270 else reply

        except Exception as e:
            logging.error(f"خطأ توليد رد: {e}")
            return f"مرحبًا @{username}، واجهت مشكلة مؤقتة. سأعود قريبًا 🚀"

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"متصل بنجاح → @{me.username}")

            # نشر حالة (مع timestamp لتجنب duplicate)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = f"🚀 TechAgent Pro جاهز\nتحليل تقني + مقارنات دقيقة 📊\n🕒 {now}"
            self.x_client.create_tweet(text=status)
            logging.info("تم نشر تغريدة الحالة")

            # جلب المنشنات
            mentions = self.x_client.get_users_mentions(
                id=me.id,
                max_results=15,
                expansions=["author_id"],
                user_fields=["username"],
                tweet_fields=["created_at"]
            )

            if not mentions.data:
                logging.info("لا منشنات جديدة")
                return

            users = {u.id: u.username for u in mentions.includes.get("users", [])}

            for tweet in mentions.data:
                author = users.get(tweet.author_id, "مستخدم")
                logging.info(f"منشن من @{author}")

                reply_text = self._generate_response(tweet.text, author)

                self.x_client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=tweet.id
                )
                logging.info(f"تم الرد على @{author}")

        except tweepy.TooManyRequests:
            logging.warning("Rate limit → سيتم إعادة المحاولة لاحقًا")
        except Exception as e:
            logging.error(f"خطأ في run(): {e}", exc_info=True)

if __name__ == "__main__":
    logging.info("تشغيل TechAgent Pro...")
    try:
        TechAgentPro().run()
    except Exception as e:
        logging.critical(f"فشل التشغيل الكلي: {e}", exc_info=True)
