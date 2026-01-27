import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time
import sys

# 1. نظام المعالجة العربية: تم التأكد من الترتيب الصحيح لمنع النص المعكوس
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False
    print("⚠️ تحذير: مكتبات المعالجة العربية مفقودة.")

logging.basicConfig(level=logging.INFO, format='%(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v76.0 [Final Stable Build] ===")
        
        # إعداد الاتصال واستدعاء المفاتيح من GitHub Secrets
        try:
            self.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            self.client_v2 = tweepy.Client(
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )

            auth = tweepy.OAuth1UserHandler(
                os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
                os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
            )
            self.api_v1 = tweepy.API(auth)
            logging.info("✅ تم ربط APIs بنجاح.")
        except Exception as e:
            logging.error(f"❌ خطأ في التهيئة: {e}")

        self.system_instr = (
            "أنت TechAgent. خبير تقني محترف. "
            "في النشر الاستهدافي: Hook قوي، مصطلحات تقنية مزدوجة، سؤال جدلي في النهاية. "
            "في الردود الذكية: ردود تقنية، منطقية، وجدلية قصيرة. الختم دائماً بـ +#"
        )

    def _fix_text(self, text):
        """معالجة متقدمة للنص العربي لضمان الاتصال والاتجاه الصحيح"""
        if AR_SUPPORT:
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
        return text

    def _create_visual(self, content):
        """توليد صورة احترافية مع تلافي أخطاء المسارات والمحاذاة السابقة"""
        try:
            width, height = 1200, 1100
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            
            # تحديد المسار بدقة داخل مجلد tech-ai-bot
            base_path = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(base_path, "font.ttf")
            
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 42)
                font_bold = ImageFont.truetype(font_path, 65)
            else:
                logging.error(f"❌ ملف الخط غير موجود في: {font_path}")
                font = font_bold = ImageFont.load_default()

            # رسم العنوان بمحاذاة يمين دقيقة (anchor='ra')
            title = self._fix_text("تحليل TechAgent الاستهدافي")
            d.text((width - 100, 100), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            
            # معالجة محتوى النص
            y_pos = 280
            lines = content.split('\n')
            for line in lines:
                if not line.strip(): continue
                # التفاف النص العربي بشكل سليم
                wrapped_lines = textwrap.wrap(line, width=50)
                for w_line in wrapped_lines:
                    d.text((width - 100, y_pos), self._fix_text(w_line.strip()), fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += 75
            
            # إضافة المصدر في أسفل الصورة (تم التأكد من إغلاق كافة الأقواس هنا)
            source_txt = self._fix_text("نظام تحليل TechAgent v76.0")
            d.text((width - 100, height - 100), source_txt, fill=(148, 163, 184), font=font, anchor="ra")
            
            output_path = os.path.join(base_path, "tech_output.png")
            img.save(output_path)
            return output_path
        except Exception as e:
            logging.error(f"❌ خطأ في دالة الرسم: {e}")
            return None

    def _interact(self):
        """نظام الردود الذكية (Smart Replies) المستهدف للإشارات الجديدة"""
        logging.info("--- بدء فحص الردود الذكية ---")
        try:
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            
            if mentions and mentions.data:
                for tweet in mentions.data:
                    logging.info(f"📩 معالجة منشن من ID: {tweet.id}")
                    prompt = f"رد بأسلوب تقني ذكي وجدلي ومختصر جداً على: {tweet.text}"
                    
                    resp = self.ai_client.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}]
                    )
                    reply = resp.choices[0].message.content.strip()
                    
                    self.client_v2.create_tweet(text=f"{reply}", in_reply_to_tweet_id=tweet.id)
                    logging.info("✅ تم إرسال الرد الذكي.")
            else:
                logging.info("ℹ️ لا يوجد منشن جديد.")
        except Exception as e:
            logging.error(f"❌ خطأ في نظام التفاعل: {e}")

    def _post(self):
        """نشر استهدافي مع صورة احترافية"""
        try:
            topics = ["مستقبل معالجات 2026", "الذكاء الاصطناعي وجدل الوظائف", "تطور الهواتف القابلة للطي"]
            topic = random.choice(topics)
            prompt = f"اكتب تغريدة استهدافية بـ Hook قوي عن {topic} مع مصطلحات إنجليزية وسؤال جدلي."
            
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}]
            )
            content = resp.choices[0].message.content.strip()
            
            image_path = self._create_visual(content)
            
            if image_path and os.path.exists(image_path):
                # رفع الوسائط عبر API v1.1
                media = self.api_v1.media_upload(image_path)
                self.client_v2.create_tweet(
                    text=f"🚀 تحليل تقني جديد..\n\n#تقنية #TechAgent #2026 +#",
                    media_ids=[media.media_id]
                )
                logging.info("✅ تم النشر الاستهدافي مع الصورة.")
            else:
                self.client_v2.create_tweet(text=f"{content}\n\n+#")
                logging.info("✅ تم النشر نصياً فقط.")
        except Exception as e:
            logging.error(f"❌ خطأ في عملية النشر: {e}")

    def run(self):
        self._post()
        time.sleep(15) # فاصل زمني بسيط
        self._interact()

if __name__ == "__main__":
    agent = TechAgentUltimate()
    agent.run()
