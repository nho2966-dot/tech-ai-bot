import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time

# نظام حماية استيراد المكتبات لضمان التشغيل المستمر
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False
    logging.warning("⚠️ مكتبات RTL مفقودة! سيتم استخدام النص الخام.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v70.0 [Smooth & Professional] ===")
        
        # إعداد المحرك الذكي والاتصال بـ X
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        self.api_v1 = tweepy.API(auth)
        self.client_v2 = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # ضبط نبرة الصوت: خبير، سلس، ويدمج المصطلحات الإنجليزية
        self.system_instr = (
            "أنت TechAgent. وكيل تقني محترف بأسلوب سلس وممتع. "
            "قاعدتك: استخدم المصطلحات التقنية بالإنجليزية (Technical Terms) "
            "مع ذكر تعريبها أو شرحها العربي في السياق. "
            "مثال: 'خوارزميات التعلم العميق (Deep Learning)'. "
            "الأسلوب: تفاعلي، ذكي، غير جاف. الختم دائماً بـ +#. "
            "المحتوى: تقنيات 2026، AI، هاردوير، وسيو المنصات."
        )

    def _fix_text(self, text):
        """معالجة النص العربي لليمن إلى اليسار"""
        if AR_SUPPORT:
            return get_display(arabic_reshaper.reshape(text))
        return text

    def _create_visual(self, content):
        """توليد صورة احترافية مع هوامش أمان 100px ومحاذاة يمين"""
        try:
            width, height = 1200, 1000
            padding = 100
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            
            # تحميل الخط العربي (تأكد من وجود الملف في المجلد)
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()

            title = self._fix_text("تقرير TechAgent التقني")
            d.text((width - padding, 60), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            
            y_pos = 220
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    d.text((width - padding, y_pos), self._fix_text(w_line.strip()), fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += 65
            
            path = "tech_output.png"
            img.crop((0, 0, width, min(y_pos + 100, height))).save(path)
            return path
        except Exception as e:
            logging.error(f"Image Visual Error: {e
