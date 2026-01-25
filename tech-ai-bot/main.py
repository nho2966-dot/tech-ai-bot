import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime

# ─── إعداد السجلات (للمراقبة الاحترافية عبر GitHub) ──────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

class TechAgentPro:
    def __init__(self):
        logging.info("🚀 بدء تشغيل TechAgent Pro (النسخة المحدثة)")
        
        # تحميل الإعدادات
        self.config = self._load_config()

        # إعداد عميل X (باستخدام v2 API)
        # ملاحظة: تأكد أن المفاتيح في GitHub Secrets هي التي ولّدتها "بعد" الاشتراك
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # إعداد OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("❌ OPENAI_API_KEY مفقود في الإعدادات")
        
        self.ai_client = OpenAI(api_key=api_key)
        self.model = self.config.get("api", {}).get("openai", {}).get("model", "gpt-4o-mini")

    def _load_config(self):
        """تحميل config.yaml مع دعم GitHub Secrets كبديل"""
        secret_yaml = os.getenv("CONFIG_YAML")
        if secret_yaml:
            try:
                return yaml.safe_load(secret_yaml)
            except Exception: pass

        target = "config.yaml"
        workspace = os.getenv("GITHUB_WORKSPACE", os.getcwd())
        for root, _, files in os.walk(workspace):
            if target in files:
                with open(os.path.join(root, target), encoding="utf-8") as f:
                    return yaml.safe_load(f)
        
        # إعدادات افتراضية في حال فقدان الملف
        return {"sources": {"trusted_domains": ["techcrunch.com", "theverge.com"]}}

    def _generate_response(self, tweet_text: str, username: str) -> str:
        """توليد الرد التقني بناءً على القواعد الـ 7"""
        system_prompt = f"""
        أنت TechAgent Pro – خبير تقني محايد.
        القواعد:
        1. رد بلغة المستخدم {username}.
        2. استخدم جداول Markdown للمقارنات 📊.
        3. المصادر المعتمدة: {', '.join(self.config.get('sources', {}).get('trusted_domains', []))}.
        4. إذا لم تجد معلومة حديثة: قل 'لا توجد معلومات موثوقة حديثة'.
        5. الرد قصير (< 280 حرف) وينتهي بسؤال متابعة ذكي.
        6. لا تطلب بيانات شخصية.
        7. استخدم الإيموجي (🚀, 📊, 🖼️) بذكاء.
        """
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"السؤال من {username}: {tweet_text}"}
                ],
                max_tokens=150,
                temperature=0.5
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return f"عذراً @{username}، أواجه ضغطاً في العمل. سأعود للرد قريباً! 🚀"

    def run(self):
        try:
            # التحقق من هوية البوت
            me = self.x_client.get_me().data
            if not me:
                raise Exception("فشل الاتصال بالحساب. تأكد من صحة الـ Tokens.")
            logging.info(f"✅ متصل كـ @{me.username}")

            # 1. نشر تغريدة الحالة (فريدة لمنع خطأ التكرار 403)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = f"🚀 TechAgent Pro: متصل وبكامل طاقته!\nنظام التحليل التقني والمقارنات المحدث جاهز 📊\n\n🕒 تحديث: {now}"
            
            logging.info("جاري محاولة نشر التغريدة...")
            post_resp = self.x_client.create_tweet(text=status)
            
            if post_resp.data:
                logging.info(f"✨ نجح النشر! معرف التغريدة: {post_resp.data['id']}")
            
            # 2. فحص والرد على المنشنات
            mentions = self.x_client.get_users_mentions(
                id=me.id,
                max_results=10,
                expansions=["author_id"],
                user_fields=["username"]
            )

            if mentions.data:
                users = {u.id: u.username for u in mentions.includes.get("users", [])}
                for tweet in mentions.data:
                    author = users.get(tweet.author_id, "user")
                    logging.info(f"جاري الرد على منشن من @{author}")
                    
                    reply = self._generate_response(tweet.text, author)
                    self.x_client.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    logging.info(f"✅ تم الإرسال إلى @{author}")
            else:
                logging.info("لا توجد منشنات جديدة للرد عليها.")

        except tweepy.Forbidden as e:
            logging.error(f"❌ خطأ 403 (Forbidden): تأكد من عمل Regenerate للمفاتيح بعد تفعيل اشتراكك وتغيير الصلاحيات لـ Read/Write.")
        except Exception as e:
            logging.error(f"❌ خطأ غير متوقع: {e}", exc_info=True)

if __name__ == "__main__":
    TechAgentPro().run()
