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
        logging.info("=== TechAgent Pro v74.0 [Structure Fixed] ===")
        
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
            # إعادة تشكيل الحروف لتتصل ببعضها
            reshaped_text = arabic_reshaper.reshape(text)
            # تصحيح الاتجاه من اليمين لليسار
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
                logging.warning("⚠️ ملف الخط font.ttf غير موجود في المسار!")
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
            
            # إضافة المصدر
            source_txt = self._fix
