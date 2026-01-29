import os
import json
import logging
import tweepy
import yaml
from openai import OpenAI
from datetime import datetime

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProPaid:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Paid Tier Mode] ---")
        
        # 1. الإعدادات الافتراضية (خطة احتياطية)
        self.config = {
            'content': {
                'system_instruction': (
                    "أنت خبير تقني عربي محترف. القواعد: "
                    "1. العربية الفصحى البسيطة فقط. "
                    "2. الأسلوب تفاعلي، ذكي، ومبهر. "
                    "3. المد بالواو يتطلب ضم الشفتين جيداً عند نطق الحرف الممدود (مثال: حاسوب، تكنولوجيا، تطوير)."
                )
            },
            'api': {
                'reply_model': "openai/gpt-4o-mini"
            },
            'paths': {'state_file': "state.json"}
        }

        # 2. محاولة تحميل الإعدادات من config.yaml إذا وجد
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    ext_cfg = yaml.safe_load(f)
                    if ext_cfg: self.config.update(ext_cfg)
                    logging.info("✅ تم تحميل الإعدادات الخارجية.")
            except: logging.warning("⚠️ فشل تحميل YAML، سأستخدم الإعدادات المدمجة.")

        # 3. إعداد الاتصال بـ X (نسخة v2 المخصصة للمدفوع)
        try:
            ak = os.environ.get("X_API_KEY", "").strip()
            asec = os.environ.get("X_API_SECRET", "").strip()
            at = os.environ.get("X_ACCESS_TOKEN", "").strip()
            atsec = os.environ.get("X_ACCESS_SECRET", "").strip()

            self.client_v2 = tweepy.Client(
                consumer_key=ak,
                consumer_secret=asec,
                access_token=at,
                access_token_secret=atsec,
                wait_on_rate_limit=True
            )
            
            # التحقق من الحساب
            me = self.client_v2.get_me()
            logging.info(f"✅ متصل بنجاح كحساب مدفوع: {me.data.username}")
            
        except Exception as e:
            logging.error(f"❌ خطأ في المصادقة (تحقق من المفاتيح وصلاحيات v2): {e}")
            raise

        # 4. إعداد OpenAI/OpenRouter
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        self.state_path = os.path.join(base_dir, self.config['paths']['state_file'])
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"replied_to": []}

    def run(self):
        try:
            logging.info(f"🕒 مزامنة الوقت (UTC): {datetime.utcnow()}")
            
            # استهداف ذكي: كلمات تقنية، لغة عربية، استبعاد الريتويت والردود
            query = "(تكنولوجيا OR ذكاء_اصطناعي OR برمجة OR تقنية) lang:ar -is:retweet -is:reply"
            
            tweets = self.client_v2.search_recent_tweets(
                query=query, 
                max_results=10,
                tweet_fields=['id', 'text']
            )
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state["replied_to"]: continue
                    
                    logging.info(f"📝 جاري معالجة التغريدة: {tweet.id}")
                    
                    # توليد رد ذكي
                    res = self.ai_client.chat.completions.create(
                        model=self.config['api']['reply_model'],
                        messages=[
                            {"role": "system", "content": self.config['content']['system_instruction']},
                            {"role": "user", "content": f"رد بأسلوب خبير على هذه التغريدة: {tweet.text}"}
                        ]
                    )
                    reply_text = res.choices[0].message.content.strip()
                    
                    # تنفيذ الرد باستخدام API v2 (الخيار الأضمن للمدفوع)
                    self.client_v2.create_tweet(
                        text=reply_text[:280],
                        in_reply_to_tweet_id=tweet.id
                    )
                    
                    self.state["replied_to"].append(tweet.id)
                    logging.info(f"✅ تم الرد بنجاح على: {tweet.id}")
                    break # رد واحد في كل دورة لتجنب الحظر
            else:
                logging.info("🔎 لم يتم العثور على تغريدات جديدة مطابقة للبحث.")

            # حفظ الحالة
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"❌ خطأ أثناء التشغيل: {e}")

if __name__ == "__main__":
    TechExpertProPaid().run()
