import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time
import sys

# التأكد من استيراد مكتبات المعالجة العربية
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False

logging.basicConfig(level=logging.INFO, format='%(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v74.1 [Syntax Fixed] ===")
        
        # إعداد الاتصال
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

        self.system_instr = (
            "أنت TechAgent. خبير تقني وصانع محتوى ممتع. "
            "ابدأ بـ Hook خاطف، استخدم مصطلحات تقنية إنجليزية مع تعريبها، "
            "واختم دائماً بسؤال جدلي يثير النقاش. الختم +#"
        )

    def _fix_text(self, text):
        """إصلاح النص العربي المقطع والمعكوس"""
        if AR_SUPPORT:
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
        return text

    def _create_visual(self, content):
        """توليد صورة احترافية مع مراعاة هيكلة المجلدات"""
        try:
            width, height = 1200, 1000
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            
            # المسار بناءً على الهيكلة المحفوظة
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 40)
                font_bold = ImageFont.truetype(font_path, 60)
            else:
                logging.warning("⚠️ ملف الخط font.ttf غير موجود!")
                font = font_bold = ImageFont.load_default()

            # رسم العنوان
            title = self._fix_text("تحليل TechAgent التقني")
            d.text((width - 80, 80), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            
            # رسم المحتوى
            y_pos = 250
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    d.text((width - 80, y_pos), self._fix_text(w_line.strip()), fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += 75
            
            # إضافة المصدر (تم تصحيح السطر الذي سبب الخطأ)
            source_txt = self._fix_text("المصدر: وحدة ذكاء TechAgent v74.1")
            d.text((width - 80, y_pos + 80), source_txt, fill=(148, 163, 184), font=font, anchor="ra")
            
            save_path = "tech_output.png"
            img.save(save_path)
            return save_path
        except Exception as e:
            logging.error(f"❌ خطأ في إنشاء الصورة: {e}")
            return None

    def _post(self):
        try:
            topics = [
                "مستقبل الـ NPU في 2026", 
                "صراع كروت الشاشة RTX 5090", 
                "الذكاء الاصطناعي التوليدي في البرمجة"
            ]
            topic = random.choice(topics)
            
            prompt = f"اكتب تغريدة تسويقية بأسلوب Hook مثير عن {topic} مع مصطلحات إنجليزية وسؤال جدلي."
            
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}]
            )
            content = resp.choices[0].message.content.strip()
            
            image_path = self._create_visual(content)
            
            if image_path and os.path.exists(image_path):
                media = self.api_v1.media_upload(image_path)
                self.client_v2.create_tweet(
                    text=f"🚀 جديدنا اليوم من TechAgent..\n\n{content[:150]}...\n\n#تقنية #2026 +#",
                    media_ids=[media.media_id]
                )
                logging.info("✅ تم النشر مع الصورة بنجاح!")
            else:
                self.client_v2.create_tweet(text=f"{content}\n\n+#")
                logging.info("✅ تم النشر نصياً فقط!")

        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")

    def run(self):
        self._post()

if __name__ == "__main__":
    agent = TechAgentUltimate()
    agent.run()
