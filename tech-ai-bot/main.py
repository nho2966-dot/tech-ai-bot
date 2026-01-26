import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime, timedelta
import random
import time
import hashlib

# ─── إعداد السجل ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

LAST_TWEET_FILE = "last_tweet_hash.txt"  # لمنع التكرار

class TechAgentPro:
    def __init__(self):
        logging.info("=== TechAgent Pro v6 – تركيز على المستقبل والسبق الصحفي ===")
        logging.info(f"المسار الحالي: {os.getcwd()}")

        self.config = self._load_config()

        # ─── اتصال AI (OpenRouter أولوية + OpenAI fallback) ──────────────
        router_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if router_key:
            logging.info("استخدام OpenRouter")
            self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=router_key)
            self.model = "alibabacloud/qwen-2.5-72b-instruct"  # قوي في التوقعات والعربية
        elif openai_key:
            logging.info("استخدام OpenAI")
            self.ai_client = OpenAI(api_key=openai_key)
            self.model = "gpt-4o-mini"
        else:
            raise ValueError("مفاتيح AI مفقودة")

        logging.info(f"النموذج: {self.model}")

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
        logging.info(f"البوت: @{self.my_username}")

        # إعدادات النشر المستقبلي والأمان
        self.daily_posts_target = 2
        self.min_delay_between_posts = 900   # 15 دقيقة
        self.max_delay_between_posts = 3600  # ساعة
        self.max_replies_per_run = 4
        self.min_followers_to_reply = 40

    def _load_config(self):
        secret = os.getenv("CONFIG_YAML")
        if secret:
            logging.info("تحميل من Secret CONFIG_YAML")
            return yaml.safe_load(secret)

        logging.warning("استخدام افتراضي")
        return {
            "behavior": {
                "daily_posts_target": 2,
                "min_delay_between_posts": 900,
                "max_delay_between_posts": 3600,
                "max_replies_per_run": 4,
                "min_followers_to_reply": 40,
                "spam_keywords": ["crypto", "airdrop", "giveaway", "claim", "free", "bot"]
            }
        }

    def _was_similar_tweet_posted_today(self, content: str) -> bool:
        if not os.path.exists(LAST_TWEET_FILE):
            return False
        try:
            with open(LAST_TWEET_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    h, t = line.strip().split("|")
                    if datetime.now() - datetime.fromisoformat(t) < timedelta(hours=24):
                        if hashlib.md5(content.encode()).hexdigest() == h:
                            return True
        except:
            return False
        return False

    def _save_tweet_hash(self, content: str):
        h = hashlib.md5(content.encode()).hexdigest()
        with open(LAST_TWEET_FILE, "a", encoding="utf-8") as f:
            f.write(f"{h}|{datetime.now().isoformat()}\n")

    def _generate_future_tech_tweet(self):
        today = datetime.now().strftime("%Y-%m-%d")
        next_year = (datetime.now() + timedelta(days=365)).strftime("%Y")

        prompt = f"""
        التاريخ اليوم {today}. أنت خبير تقني متخصص في التوقعات المستقبلية والسبق الصحفي.
        اكتب تغريدة تقنية بالعربية الفصحى عن تطور تقني متوقع خلال {today}–{next_year}.
        القواعد الصارمة:
        - ركز على السبق الصحفي المستقبلي (مثل ميزات AI قادمة، أجهزة 2027، تغييرات في الألعاب أو الخصوصية).
        - استند إلى اتجاهات حديثة موثوقة فقط (مثل CES 2026، تقارير The Verge، TechCrunch).
        - اذكر مصدر موثوق أو قل 'توقع مبني على اتجاهات حالية' أو 'غير مؤكد رسميًا'.
        - ابدأ بـ '🚀 المستقبل:' أو '🔮 توقع 2027:' أو '📈 سبق صحفي محتمل'.
        - اجعلها دقيقة، مفيدة، جذابة، مع إيموجي احترافي وهاشتاغات.
        - أقل من 270 حرف.
        - انهِ بسؤال مفتوح قوي للتفاعل.
        - التغريدة مكتملة، ذات معنى، وليست مجرد عنوان.
        """

        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=280,
                temperature=0.72
            )
            content = resp.choices[0].message.content.strip()

            # ضمان الجودة والاكتمال
            if len(content) < 100 or content.count('.') < 3 or "..." in content * 3:
                logging.warning("تغريدة غير مكتملة → إعادة محاولة")
                return self._generate_future_tech_tweet()  # إعادة محاولة مرة واحدة

            if len(content) > 270:
                content = content[:267] + "…"

            return content
        except Exception as e:
            logging.error(f"خطأ توليد تغريدة مستقبلية: {e}")
            return None

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"متصل → @{me.username}")

            # نشر تغريدتين مستقبليتين يوميًا
            posted = 0
            while posted < 2:
                content = self._generate_future_tech_tweet()
                if not content:
                    break

                if self._was_similar_tweet_posted_today(content):
                    logging.info("محتوى مشابه موجود → تخطي")
                    break

                self.x_client.create_tweet(text=content)
                logging.info(f"✨ تم نشر التغريدة المستقبلية رقم {posted+1}: {content[:60]}...")
                self._save_tweet_hash(content)
                posted += 1

                if posted < 2:
                    delay = random.randint(900, 3600)  # 15–60 دقيقة
                    logging.info(f"انتظار {delay//60} دقيقة قبل التغريدة الثانية...")
                    time.sleep(delay)

            if posted == 0:
                logging.warning("لم يتم نشر أي تغريدة اليوم")

        except Exception as e:
            logging.error(f"خطأ عام: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        TechAgentPro().run()
    except Exception as e:
        logging.critical(f"فشل كلي: {e}", exc_info=True)
