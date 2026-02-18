import os
import sqlite3
import logging
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
# استيراد الأدوات من المجلدات اللي عندك
from src.core.ai_writer import AIWriter 
from src.utils.logger import setup_logger

class NasserApexBot:
    def __init__(self):
        # ربط قواعد البيانات اللي في ملفاتك
        self.db_path = "sovereign_apex_v311.db"
        self.font_path = "font.ttf" # الخط الموجود في جذع المشروع
        self.logger = setup_logger()
        self.writer = AIWriter()

    def generate_safe_visual(self, text_content, bg_path="templates/bg_ai.png"):
        """
        توليد محتوى بصري احترافي:
        1. التحقق من لغة النص (خالي من الأخطاء).
        2. دمج النص فوق الصورة باستخدام الخط المرفق.
        """
        try:
            # تدقيق النص قبل الرسم (مرحلة منع الهلوسة اللفظية)
            clean_text = self.writer.validate_arabic(text_content)
            
            # معالجة النص العربي للحروف المقطعة (Arabic Reshaper)
            reshaped_text = arabic_reshaper.reshape(clean_text)
            display_text = get_display(reshaped_text)

            # فتح القالب البصري
            img = Image.open(bg_path)
            draw = ImageDraw.Draw(img)
            
            # استخدام الخط الموجود في ملفاتك (font.ttf)
            font = ImageFont.truetype(self.font_path, 40)
            
            # رسم النص (أبيض بظل خفيف لضمان الوضوح)
            position = (50, 400)
            draw.text(position, display_text, font=font, fill="white")
            
            output_path = "src/web/static/latest_infographic.png"
            img.save(output_path)
            return output_path
            
        except Exception as e:
            self.logger.error(f"❌ خطأ في إنتاج المحتوى البصري: {e}")
            return None

    def handle_cycle(self):
        """الدورة الكاملة بناءً على ملفات المشروع"""
        # 1. صيد الترند (Trend Hunter)
        # 2. كتابة المحتوى (AI Writer)
        # 3. إذا كان المحتوى يحتاج صورة -> استدعاء generate_safe_visual
        # 4. النشر (Publisher)
        pass

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.handle_cycle()
