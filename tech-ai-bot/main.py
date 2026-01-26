import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import random
import time

# إعداد السجل التقني
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v41.0 [Final Visual Fix] ===")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # إعداد X API (v1.1 للصور و v2 للنشر)
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

    def _create_visual_card(self, content):
        """توليد البطاقة البصرية مع دعم كامل للخط العربي"""
        try:
            img = Image.new('RGB', (1100, 900), color=(11, 15, 20)) # خلفية داكنة احترافية
            d = ImageDraw.Draw(img)
            
            # تحديد مسار الخط بدقة (يجب أن يكون font.ttf بجانب main.py)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(current_dir, "font.ttf")
            
            if os.path.exists(font_path):
                font_title = ImageFont.truetype(font_path, 55)
                font_body = ImageFont.truetype(font_path, 34)
                logging.info(f"✅ تم تحميل الخط بنجاح من: {font_path}")
            else:
                logging.error(f"❌ خطأ: ملف font.ttf غير موجود في {current_dir}")
                font_title = font_body = ImageFont.load_default()

            # رسم العنوان العلوي
            d.text((60, 50), "TECHAGENT INTEL | 2026", fill=(29, 155, 240), font=font_title)
            
            # رسم الأسطر مع معالجة المسافات
            y_pos = 180
            for line in content.split('\n'):
                clean_line = line.strip()
                if clean_line:
                    d.text((60, y_pos), clean_line, fill=(235, 240, 245), font=font_body)
                    y_pos += 65
            
            path = "tech_card_final.png"
            img.save(path)
            return path
        except Exception as e:
            logging.error(f"Rendering Error: {e}")
            return None

    def _generate_content(self, topic):
        """توليد محتوى تقني مكثف للشباب"""
        prompt = (
            f"أنت TechAgent. قدم تحليل تقني جاف وعميق (5 نقاط) حول: {topic}. "
            "ممنوع استخدام Markdown أو رموز زخرفية. الختم بـ +#."
        )
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def run(self):
        """تشغيل دورة النشر"""
        topics = [
            "مستقبل البرمجة مع AI Agents لعام 2026",
            "تسريبات Snapdragon 8 Gen 5 vs Apple A19",
            "أدوات AI لزيادة دخل المبرمجين المستقلين"
        ]
        topic = random.choice(topics)
        content = self._generate_content(topic)
        
        if content:
            path = self._create_visual_card(content)
            if path:
                try:
                    media = self.api_v1.media_upload(path)
                    tweet_text = f"🚨 تحليل تقني: {topic}\n\nبيانات جافة لجيل المحترفين. 👇\n\n+#"
                    self.client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                    logging.info("🚀 تم نشر التغريدة بنجاح!")
                except Exception as e:
                    logging.error(f"X Post Error: {e}")

if __name__ == "__main__":
    TechAgentUltimate().run()
