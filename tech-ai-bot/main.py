import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime
import random
import time

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

        self.config = self._load_config()

        # ─── دعم OPENROUTER أو OpenAI ───────────────────────────────────────
        router_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if router_key:
            logging.info("استخدام OpenRouter")
            self.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=router_key
            )
            self.model = self.config.get("api", {}).get("openrouter", {}).get("model", "anthropic/claude-3.5-sonnet")
        elif openai_key:
            logging.info("استخدام OpenAI")
            self.ai_client = OpenAI(api_key=openai_key)
            self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")
        else:
            raise ValueError("يجب توفير OPENROUTER_API_KEY أو OPENAI_API_KEY")

        logging.info(f"النموذج المستخدم: {self.model}")

        # ─── اتصال X ────────────────────────────────────────────────────────
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        me = self.x_client.get_me().data
        self.my_id = me.id
        self.my_username = me.username.lower()
        logging.info(f"حساب البوت: @{self.my_username}")

        # إعدادات لتجنب الخوارزمية / الحظر
        self.max_replies_per_run = self.config["behavior"].get("max_replies_per_run", 5)
        self.min_followers_to_reply = self.config["behavior"].get("min_followers_to_reply", 30)
        self.reply_delay_min_sec = self.config["behavior"].get("reply_delay_min_sec", 25)
        self.reply_delay_max_sec = self.config["behavior"].get("reply_delay_max_sec", 90)

    def _load_config(self):
        secret = os.getenv("CONFIG_YAML")
        if secret:
            logging.info("تحميل من Secret CONFIG_YAML")
            try:
                return yaml.safe_load(secret)
            except Exception as e:
                logging.error(f"خطأ تحليل Secret: {e}")

        logging.warning("استخدام إعدادات افتراضية")
        return {
            "api": {
                "openai": {"model": "gpt-4o-mini"},
                "openrouter": {"model": "anthropic/claude-3.5-sonnet"}
            },
            "behavior": {
                "max_replies_per_run": 5,
                "min_followers_to_reply": 30,
                "reply_delay_min_sec": 25,
                "reply_delay_max_sec": 90,
                "publish_status_tweet": False,  # تعطيل مؤقت لتجنب التكرار
                "spam_keywords": ["crypto", "airdrop", "giveaway", "claim", "free", "bot", "earn", "token"]
            },
            "sources": {
                "trusted_domains": [
                    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
                    "cnet.com", "engadget.com", "bloomberg.com", "reuters.com"
                ]
            }
        }

    def _should_skip_tweet(self, tweet, author_followers: int) -> bool:
        """تصفية المنشنات لتجنب السبام والحظر"""
        text_lower = tweet.text.lower()

        # تجاهل المنشنات من الحساب نفسه
        if tweet.author_id == self.my_id:
            logging.debug("تخطي: منشن من الحساب نفسه")
            return True

        # تجاهل الحسابات الصغيرة جدًا
        if author_followers < self.min_followers_to_reply:
            logging.info(f"تخطي @{tweet.author_id} – متابعون قليلون: {author_followers}")
            return True

        # تجاهل المنشنات التي تحتوي كلمات سبام شائعة
        if any(kw in text_lower for kw in self.config["behavior"]["spam_keywords"]):
            logging.info(f"تخطي منشن محتمل سبام: {text_lower[:60]}...")
            return True

        return False

    def _generate_response(self, tweet_text: str, username: str) -> str:
        trusted = self.config.get("sources", {}).get("trusted_domains", [])

        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني محايد ومهني متخصص في:
        • الذكاء الاصطناعي وتطبيقاته
        • منصات التواصل الاجتماعي واستراتيجيات التفاعل
        • الألعاب الإلكترونية وتحديثاتها
        • التسريبات التقنية الموثوقة
        • الأجهزة الذكية ومقارناتها
        • السبق الصحفي التقني

        القواعد الصارمة:
        1. الرد بلغة التغريدة (@{username}).
        2. لا تقدم معلومة تقنية محددة إلا مدعومة بمصدر من: {', '.join(trusted)}
        3. إذا لم يكن هناك مصدر موثوق حديث → قل: 'لا توجد معلومات موثوقة حديثة متاحة حالياً'
        4. الرد أقل من 270 حرف، مهني، يفتح نقاشًا ذكيًا، ينتهي بسؤال مفتوح.
        5. لا تطلب أي بيانات شخصية أبدًا.
        6. استخدم إيموجي بحذر واحترافية فقط (مثل 📱، 🚀، 📊).
        """

        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"@{username} كتب: {tweet_text}\nرد احترافي موجز فقط."}
                ],
                temperature=0.58,
                max_tokens=140
            )
            reply = resp.choices[0].message.content.strip()
            return reply[:267] + "…" if len(reply) > 270 else reply

        except Exception as e:
            logging.error(f"خطأ توليد رد: {e}")
            return f"@{username} مرحبًا! واجهت مشكلة مؤقتة، حاول لاحقًا 🚀"

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"متصل → @{me.username}")

            # نشر حالة (معطل مؤقتًا لتجنب التكرار)
            if self.config["behavior"].get("publish_status_tweet", False):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status = f"🚀 TechAgent Pro جاهز (بـ {self.model})\nتحليل تقني + ردود ذكية 📊\n🕒 {now}"
                self.x_client.create_tweet(text=status)
                logging.info("تم نشر تغريدة الحالة")
            else:
                logging.info("نشر الحالة معطل من الإعدادات")

            # جلب المنشنات
            mentions = self.x_client.get_users_mentions(
                id=me.id,
                max_results=20,
                expansions=["author_id"],
                user_fields=["username", "public_metrics"]
            )

            if not mentions.data:
                logging.info("لا منشنات جديدة")
                return

            users = {}
            for u in mentions.includes.get("users", []):
                users[u.id] = {
                    "username": u.username,
                    "followers": u.public_metrics.get("followers_count", 0)
                }

            replied_count = 0
            max_replies = self.config["behavior"].get("max_replies_per_run", 8)

            for tweet in mentions.data:
                if replied_count >= max_replies:
                    logging.info("وصل الحد الأقصى للردود في هذه الدورة")
                    break

                author_data = users.get(tweet.author_id, {"username": "مستخدم", "followers": 0})
                author = author_data["username"]
                followers = author_data["followers"]

                if self._should_skip_tweet(tweet, followers):
                    continue

                logging.info(f"معالجة منشن من @{author} ({followers} متابع)")

                reply_text = self._generate_response(tweet.text, author)

                try:
                    self.x_client.create_tweet(
                        text=reply_text,
                        in_reply_to_tweet_id=tweet.id
                    )
                    logging.info(f"تم الرد على @{author}")
                    replied_count += 1

                    # تأخير عشوائي ليبدو طبيعيًا
                    delay = random.randint(
                        self.config["behavior"]["reply_delay_min_sec"],
                        self.config["behavior"]["reply_delay_max_sec"]
                    )
                    logging.info(f"انتظار {delay} ثانية قبل الرد التالي...")
                    time.sleep(delay)

                except tweepy.TooManyRequests:
                    logging.warning("Rate limit – انتظار تلقائي")
                    break
                except tweepy.TweepyException as te:
                    logging.error(f"فشل إرسال رد لـ @{author}: {te}")

        except Exception as e:
            logging.error(f"خطأ عام في run(): {e}", exc_info=True)

if __name__ == "__main__":
    try:
        TechAgentPro().run()
    except Exception as e:
        logging.critical(f"فشل التشغيل الكلي: {e}", exc_info=True)
