import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# إعداد السجلات لمراقبة أداء البوت في GitHub Actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TechAgentPro:
    def __init__(self):
        self.config = self._find_and_load_config()
        # إعداد عملاء X و OpenAI باستخدام المفاتيح السرية
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _find_and_load_config(self):
        """البحث الشامل عن ملف الإعدادات لتجاوز تعقيد المجلدات المتداخلة"""
        target = "config.yaml"
        # البحث في بيئة عمل GitHub أولاً
        workspace = os.getenv("GITHUB_WORKSPACE", ".")
        for root, dirs, files in os.walk(workspace):
            if target in files:
                path = os.path.join(root, target)
                logging.info(f"✅ تم العثور على الإعدادات في: {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        raise FileNotFoundError("❌ لم يتم العثور على config.yaml في المستودع.")

    def _generate_response(self, text, user):
        """توليد الرد بناءً على القواعد السبعة الصارمة"""
        system_prompt = f"""
        أنت TechAgent Pro Global. التزم بالقواعد التالية في كل رد:
        1. اللغة: اكتشف لغة {user} ورد بها (عربي/إنجليزي/إلخ).
        2. المقارنات التقنية: استخدم جداول Markdown حصراً 📊.
        3. الخصوصية: ارفض أي طلب لبيانات شخصية أو خاصة بالمطور.
        4. المصادر: استند إلى النطاقات الموثوقة: {self.config.get('sources', {}).get('trusted_domains', [])}.
        5. نقص المعلومات: إذا لم تجد مصدر حديث، قل: 'لا توجد معلومات موثوقة حديثة متاحة حالياً'.
        6. هيكل الرد: ترحيب -> تحليل تقني عميق -> مصدر المعلومة -> سؤال متابعة ذكي.
        7. الوسائط: استخدم إيموجي (📊, 🖼️, 🚀) بشكل احترافي لوصف المحتوى التقني.
        """
        
        response = self.ai_client.chat.completions.create(
            model=self.config.get('api', {}).get('openai', {}).get('model', 'gpt-4o'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()

    def run(self):
        try:
            # الحصول على بيانات البوت للتأكد من الاتصال
            me = self.x_client.get_me().data
            logging.info(f"🚀 البوت متصل كـ @{me.username}")
            
            # 1. نشر تغريدة حالة فريدة (بإضافة الوقت لمنع خطأ التكرار 403)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_tweet = f"🚀 TechAgent Pro Global\nنظام التحليل التقني والمقارنات جاهز الآن 📊.\n\n🕒 وقت التشغيل: {current_time}"
            self.x_client.create_tweet(text=status_tweet)
            logging.info("Status tweet posted.")

            # 2. جلب المنشنات الجديدة والرد عليها
            mentions = self.x_client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
            if mentions.data:
                users = {u['id']: u.username for u in mentions.includes['users']}
                for tweet in mentions.data:
                    author_name = users.get(tweet.author_id)
                    logging.info(f"الرد على @{author_name}...")
                    
                    reply_text = self._generate_response(tweet.text, author_name)
                    
                    # الرد على التغريدة الأصلية
                    self.x_client.create_tweet(
                        text=reply_text[:280], # الالتزام بحدود أحرف تويتر
                        in_reply_to_tweet_id=tweet.id
                    )
                    logging.info(f"✅ تم الإرسال لـ @{author_name}")

        except Exception as e:
            if "duplicate content" in str(e).lower():
                logging.warning("⚠️ تم تخطي تغريدة الحالة لأنها مكررة (نفس الدقيقة).")
            else:
                logging.error(f"❌ خطأ في التشغيل: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
