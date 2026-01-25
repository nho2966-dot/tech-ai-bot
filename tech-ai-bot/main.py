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
        logging.info("=== بدء تشغيل TechAgent Pro ===")
        logging.info(f"المسار الحالي: {os.getcwd()}")
        logging.info(f"GITHUB_WORKSPACE: {os.getenv('GITHUB_WORKSPACE')}")
        logging.info(f"الملفات في المجلد: {os.listdir('.')[:15]}")

        # تحميل التكوين
        self.config = self._load_config()

        # ─── دعم OPENROUTER_API_KEY أولوية + fallback إلى OpenAI ──────
        router_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if router_key:
            logging.info("استخدام OPENROUTER_API_KEY (أولوية)")
            self.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=router_key
            )
            # نموذج افتراضي من OpenRouter (يمكن تغييره من config)
            self.model = self.config.get("api", {}).get("openrouter", {}).get("model", "anthropic/claude-3.5-sonnet")
        elif openai_key:
            logging.info("استخدام OPENAI_API_KEY (fallback)")
            self.ai_client = OpenAI(api_key=openai_key)
            self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")
        else:
            raise ValueError("يجب توفير واحد على الأقل من: OPENROUTER_API_KEY أو OPENAI_API_KEY في Secrets")

        logging.info(f"النموذج المستخدم: {self.model}")

        # التحقق من مفاتيح X
        x_keys = ["X_BEARER_TOKEN", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing = [k for k in x_keys if not os.getenv(k)]
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

    def _load_config(self):
        secret = os.getenv("CONFIG_YAML")
        if secret:
            logging.info("تحميل من Secret: CONFIG_YAML")
            try:
                return yaml.safe_load(secret)
            except Exception as e:
                logging.error(f"خطأ تحليل Secret: {e}")

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

        logging.warning("استخدام إعدادات افتراضية")
        return {
            "api": {
                "openai": {"model": "gpt-4o-mini"},
                "openrouter": {"model": "anthropic/claude-3.5-sonnet"}
            },
            "sources": {"trusted_domains": ["techcrunch.com", "theverge.com", "wired.com"]},
            "behavior": {"max_replies_per_hour": 10}
        }

    def _generate_response(self, tweet_text: str, username: str) -> str:
        trusted = self.config.get("sources", {}).get("trusted_domains", [])

        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني محايد ومهني.
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

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = f"🚀 TechAgent Pro جاهز (بـ {self.model})\nتحليل تقني + ردود ذكية 📊\n🕒 {now}"
            self.x_client.create_tweet(text=status)
            logging.info("تم نشر الحالة")

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
                logging.info(f"تم الرد على @{author}")

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
