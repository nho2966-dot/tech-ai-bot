import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

class TechAgentPro:
    def __init__(self):
        logging.info("🚀 تشغيل نسخة المشتركين (API v2 Only)")
        
        # إعداد عميل X بنظام v2 حصراً (المتوافق مع الباقة المدفوعة)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini" # يمكنك تغييره حسب اشتراكك في OpenAI

    def _generate_response(self, text, user):
        """توليد محتوى تقني حقيقي وأصلي"""
        system_prompt = f"أنت خبير تقني. رد على {user} بتحليل ذكي وجدول مقارنة صغير 📊 إذا لزم الأمر. اذكر مصدر تقني موثوق. الرد < 280 حرف."
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=150
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def run(self):
        try:
            # 1. التحقق من الاتصال وجلب بيانات البوت
            me = self.x_client.get_me().data
            if not me:
                logging.error("❌ تعذر جلب بيانات الحساب. تأكد من الـ Tokens.")
                return
            
            bot_id = me.id
            logging.info(f"✅ متصل كـ @{me.username}")

            # 2. نشر تغريدة الحالة (للتأكد من أن النشر يعمل)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.x_client.create_tweet(text=f"🚀 TechAgent Pro متصل (v2)\nالأنظمة تعمل بكفاءة عالية 📊\n🕒 {now}")
            logging.info("✅ تم نشر تغريدة الحالة بنجاح")

            # 3. جلب المنشنات والرد عليها (متاح للمشتركين فقط عبر v2)
            mentions = self.x_client.get_users_mentions(
                id=bot_id,
                expansions=["author_id"],
                user_fields=["username"]
            )

            if mentions.data:
                users_map = {u.id: u.username for u in mentions.includes.get("users", [])}
                for tweet in mentions.data:
                    author = users_map.get(tweet.author_id, "user")
                    
                    # منع الرد على النفس
                    if author.lower() == me.username.lower():
                        continue

                    logging.info(f"📩 معالجة طلب من @{author}")
                    reply_content = self._generate_response(tweet.text, author)
                    
                    if reply_content:
                        # الرد باستخدام v2
                        self.x_client.create_tweet(
                            text=f"@{author} {reply_content}"[:280],
                            in_reply_to_tweet_id=tweet.id
                        )
                        logging.info(f"✅ تم الرد على @{author}")
            else:
                logging.info("😴 لا توجد منشنات جديدة.")

        except tweepy.Forbidden as e:
            logging.error(f"❌ خطأ 403/453: يرجى التأكد من وضع التطبيق داخل 'Project' في Developer Portal. الباقة المدفوعة تتطلب تنظيماً معيناً للمشاريع.")
        except Exception as e:
            logging.error(f"❌ خطأ غير متوقع: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
