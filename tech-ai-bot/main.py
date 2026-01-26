import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time

# صمام أمان لاستيراد مكتبات اللغة العربية
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False
    logging.warning("⚠️ تحذير: مكتبات المعالجة العربية مفقودة. سيتم عرض النص بشكل مبسط.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v69.0 [Stability Fixed] ===")
        
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

        self.system_instr = (
            "أنت TechAgent. وكيل تقني سلس وذكي. "
            "أسلوبك ممتع وغير جاف، الختم بـ +# دائماً. "
            "تحدث عن AI، العتاد، وأسرار التقنية لعام 2026."
        )

    def _fix_arabic(self, text):
        if AR_SUPPORT:
            return get_display(arabic_reshaper.reshape(text))
        return text

    def _create_safe_visual_table(self, content):
        """صورة احترافية مع هوامش ومحاذاة يمين إجبارية"""
        try:
            width, height = 1200, 1000
            padding = 100
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()

            title = self._fix_arabic("تقرير TechAgent التقني")
            d.text((width - padding, 60), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            
            y_pos = 200
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    d.text((width - padding, y_pos), self._fix_arabic(w_line.strip()), fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += 65
            
            path = "report.png"
            img.crop((0, 0, width, min(y_pos + 100, height))).save(path)
            return path
        except Exception as e:
            logging.error(f"Image Error: {e}")
            return None

    def run(self):
        # تنفيذ دورة النشر والرد
        topic = random.choice(["أدوات AI للبرمجة", "مقارنة RTX 5090 vs 4090"])
        is_comp = "مقارنة" in topic
        
        resp = self.ai_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": f"اكتب عن {topic}"}]
        )
        content = resp.choices[0].message.content.strip()

        if is_comp:
            path = self._create_safe_visual_table(content)
            if path:
                media = self.api_v1.media_upload(path)
                self.client_v2.create_tweet(text=f"🚀 {topic}\n\nتحليلنا الجديد صار جاهز! 👇\n\n+#", media_ids=[media.media_id])
        else:
            self.client_v2.create_tweet(text=f"💡 {topic}\n\n{content}\n\n+#")
        
        logging.info("✅ تم النشر بنجاح!")

if __name__ == "__main__":
    TechAgentUltimate().run()
