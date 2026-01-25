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
        # معلومات تشخيصية لتتبع المشكلات
        logging.info("=== بدء تشغيل TechAgent Pro ===")
        logging.info(f"المسار الحالي: {os.getcwd()}")
        logging.info(f"GITHUB_WORKSPACE: {os.getenv('GITHUB_WORKSPACE')}")
        logging.info(f"الملفات في المجلد: {os.listdir('.')[:15]}")

        # تحميل التكوين
        self.config = self._load_config()

        # التحقق من مفاتيح X
        x_keys = ["X_BEARER_TOKEN", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing_x = [k for k in x_keys if not os.getenv(k)]
        if missing_x:
            raise ValueError(f"مفاتيح X مفقودة: {', '.join(missing_x)}")

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

        logging.info(f"النموذج المستخدم: {self.model}")

    def _load_config(self):
        """تحميل التكوين بأولوية: Secret → ملف → افتراضي"""
        # الأولوية 1: GitHub Secret
        secret = os.getenv("CONFIG_YAML")
        if secret:
            logging.info("تحميل من GitHub Secret → CONFIG_YAML")
            try:
                parsed = yaml.safe_load(secret)
                logging.info("تم تحليل CONFIG_YAML بنجاح")
                return parsed
            except Exception as e:
                logging.error(f"خطأ في تحليل Secret: {e}")

        # الأولوية 2: ملف config.yaml (للتطوير المحلي)
        target = "config.yaml"
        base = os.getenv("GITHUB_WORKSPACE", os.getcwd())
        logging.info(f"البحث عن {target} في: {base}")

        for root, _, files in os.walk(base):
            if target in files:
                path = os.path.join(root, target)
                logging.info(f"وجد الملف: {path}")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logging.error(f"خطأ قراءة {path}: {e}")

        # الأولوية 3: افتراضي آمن
        logging.warning("استخدام إعدادات افتراضية")
        return {
            "api": {"openai": {"model": "gpt-4o-mini"}},
            "sources": {"trusted_domains": ["techcrunch.com", "theverge.com", "wired.com"]},
            "behavior": {"max_replies_per_hour": 10}
        }

    def _generate_response(self, tweet_text: str, username: str) -> str:
        trusted = self.config.get("sources", {}).get("trusted_domains", [])

        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني محايد.
        القواعد:
        1. رد بلغة التغريدة (@{username}).
        2. لا معلومة بدون مصدر من: {', '.join(trusted)}
        3. بدون مصدر → 'لا توجد معلومات موثوقة حالياً'
        4. رد <280 حرف، مهني، ينتهي بسؤال ذكي.
        5. لا تطلب بيانات شخصية.
        """

        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"@{username}: {tweet_text}\nرد فقط."}
                ],
                temperature=0.55,
                max_tokens=140
            )
            reply = resp.choices[0].message.content.strip()
            return reply[:277] + "…" if len(reply) > 270 else reply

        except Exception as e:
            logging.error(f"خطأ توليد رد: {e}")
            return f"@{username} مرحبا! مشكلة مؤقتة، سأعود قريباً 🚀"

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"متصل → @{me.username}")

            # نشر حالة فريدة
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = f"🚀 TechAgent Pro جاهز\nتحليل + ردود ذكية 📊\n🕒 {now}"
            self.x_client.create_tweet(text=status)
            logging.info("تم نشر الحالة")

            # منشنات
            mentions = self.x_client.get_users_mentions(
                id=me.id,
                max_results=15,
                expansions=["author_id"],
                user_fields=["username"]
            )

            if not mentions.data:
                logging.info("لا منشنات جديدة")
                return

            users = {u.id: u.username for u in mentions.includes.get("users", [])}

            for tweet in mentions.data:
                author = users.get(tweet.author_id, "مستخدم")
                logging.info(f"منشن من @{author}")

                reply = self._generate_response(tweet.text, author)

                self.x_client.create_tweet(
                    text=reply,
                    in_reply_to_tweet_id=tweet.id
                )
                logging.info(f"رد على @{author}")

        except tweepy.TooManyRequests:
            logging.warning("Rate limit → انتظر")
        except Exception as e:
            logging.error(f"خطأ في run: {e}", exc_info=True)

if __name__ == "__main__":
    logging.info("تشغيل TechAgent Pro...")
    try:
        TechAgentPro().run()
    except Exception as e:
        logging.critical(f"فشل كلي: {e}", exc_info=True)
