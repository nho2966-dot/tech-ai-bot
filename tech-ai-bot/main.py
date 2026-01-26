import os
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعداد السجلات لتتبع العملية بدقة في GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s'
)

class TechAgentPro:
    def __init__(self):
        logging.info("🚀 بدء تشغيل نظام المشتركين الموثق - v2")
        
        # الاتصال باستخدام v2 (المسار الرسمي للمشتركين)
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        
        # إعداد OpenAI لإنشاء المحتوى الأصلي
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _generate_real_content(self, user_query, username):
        """توليد محتوى تقني حقيقي (جداول وتحليلات) وليس نصاً تجريبياً"""
        prompt = f"أنت خبير تقني. حلل طلب {username} التالي: '{user_query}'. رد بجدول مقارنة صغير 📊 ومعلومات دقيقة. الرد يجب أن يكون أقل من 260 حرف وموجه لـ @{username}."
        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def run(self):
        try:
            # 1. جلب بيانات البوت (للتأكد من عدم الرد على النفس)
            me = self.x_client.get_me().data
            if not me:
                logging.error("❌ فشل الاتصال. تأكد من أن الصلاحيات هي Read and Write.")
                return
            
            bot_username = me.username.lower()
            logging.info(f"✅ متصل كـ @{bot_username}")

            # 2. نشر تغريدة إثبات حالة (محتوى متغير لمنع الرفض بسبب التكرار)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.x_client.create_tweet(text=f"🚀 TechAgent Pro: الأنظمة نشطة.\nنظام تحليل البيانات والمقارنات جاهز 📊\n🕒 تحديث: {now_str}")
            logging.info("✅ تم نشر تغريدة الحالة بنجاح")

            # 3. معالجة المنشنات والرد بمحتوى حقيقي
            mentions = self.x_client.get_users_mentions(
                id=me.id,
                expansions=["author_id"],
                user_fields=["username"]
            )

            if mentions.data:
                users_map = {u.id: u.username for u in mentions.includes.get("users", [])}
                for tweet in mentions.data:
                    author = users_map.get(tweet.author_id, "user")
                    
                    # ⚠️ منع الرد على النفس
                    if author.lower() == bot_username:
                        continue

                    logging.info(f"📩 جاري إنشاء محتوى مخصص لـ @{author}...")
                    final_content = self._generate_real_content(tweet.text, author)

                    if final_content:
                        # الرد الفعلي
                        self.x_client.create_tweet(
                            text=final_content[:280],
                            in_reply_to_tweet_id=tweet.id
                        )
                        logging.info(f"✅ تم الرد بنجاح على @{author}")
            else:
                logging.info("😴 لا توجد منشنات جديدة.")

        except tweepy.Forbidden as e:
            logging.error(f"❌ خطأ 403/453: تويتر يرفض الطلب. تأكد من إعدادات OAuth 1.0a في Developer Portal.")
        except Exception as e:
            logging.error(f"❌ خطأ غير متوقع: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
