import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# ─── إعداد السجلات (للمراقبة الدقيقة) ──────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

class TechAgentPro:
    def __init__(self):
        logging.info("🚀 تشغيل النسخة الاحترافية (v1.1 + v2) مع منع الرد الذاتي")
        self.config = self._load_config()

        # إعداد الاتصال الهجين
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        self.api_v1 = tweepy.API(auth)

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")

    def _load_config(self):
        target = "config.yaml"
        workspace = os.getenv("GITHUB_WORKSPACE", os.getcwd())
        for root, _, files in os.walk(workspace):
            if target in files:
                with open(os.path.join(root, target), encoding="utf-8") as f:
                    return yaml.safe_load(f)
        return {"sources": {"trusted_domains": ["techcrunch.com", "theverge.com"]}}

    def _generate_response(self, tweet_text: str, username: str) -> str:
        """توليد محتوى جديد وحقيقي (جداول وتحليلات) بناءً على طلب المستخدم"""
        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني عالمي.
        المهمة: قم بإنشاء محتوى تقني أصلي (Original Content) رداً على {username}.
        القواعد:
        1. إذا طلب مقارنة: أنشئ جدول Markdown صغير جداً (3 صفوف كحد أقصى) 📊.
        2. المصادر: اذكر اسم مصدر موثوق واحد من {self.config.get('sources', {}).get('trusted_domains', [])}.
        3. الطول: يجب أن يكون الرد كاملاً وأقل من 260 حرفاً لضمان القبول.
        4. المحتوى: لا تستخدم ردوداً جاهزة، حلل النص وأجب بدقة.
        """
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": tweet_text}
                ],
                max_tokens=180,
                temperature=0.7 # لزيادة الإبداع وضمان عدم التكرار
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            return None

    def run(self):
        try:
            # الحصول على بيانات البوت
            me = self.x_client.get_me().data
            bot_id = me.id
            bot_username = me.username.lower()
            logging.info(f"✅ متصل كـ @{bot_username}")

            # 1. نشر تغريدة الحالة (Timestamp) لضمان عمل API
            now = datetime.now().strftime("%H:%M:%S")
            self.api_v1.update_status(status=f"🚀 TechAgent Pro: متصل.\nالأنظمة جاهزة لتحليل المنشنات 📊\n🕒 تحديث: {now}")

            # 2. جلب المنشنات
            mentions = self.x_client.get_users_mentions(
                id=bot_id,
                max_results=10,
                expansions=["author_id"],
                user_fields=["username"]
            )

            if mentions.data:
                users_map = {u.id: u.username for u in mentions.includes.get("users", [])}
                
                for tweet in mentions.data:
                    author_username = users_map.get(tweet.author_id, "").lower()
                    
                    # ⚠️ القاعدة: منع الرد على حساب البوت نفسه لتجنب الـ Loop
                    if author_username == bot_username:
                        logging.info(f"⏭️ تخطي المنشن: المصدر هو حساب البوت نفسه (@{author_username})")
                        continue

                    logging.info(f"📩 جاري إنشاء محتوى رداً على @{author_username}...")
                    
                    reply_content = self._generate_response(tweet.text, author_username)
                    
                    if reply_content:
                        try:
                            # إرسال الرد الفعلي الذي تم إنشاؤه
                            self.api_v1.update_status(
                                status=f"@{author_username} {reply_content}"[:280],
                                in_reply_to_status_id=tweet.id
                            )
                            logging.info(f"✅ تم نشر الرد المخصص لـ @{author_username}")
                        except Exception as post_err:
                            logging.error(f"❌ فشل نشر الرد: {post_err}")
            else:
                logging.info("😴 لا توجد منشنات جديدة من مستخدمين آخرين.")

        except Exception as e:
            logging.error(f"❌ خطأ عام في الدورة: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
