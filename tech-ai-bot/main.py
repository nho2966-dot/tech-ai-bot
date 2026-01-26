import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import random
import time

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v40.0 [Arabic Rendering Fix] ===")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # إعداد X API
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
        """توليد البطاقة البصرية ومعالجة مشكلة الخطوط"""
        try:
            # صورة بخلفية تقنية داكنة
            img = Image.new('RGB', (1000, 850), color=(10, 15, 20))
            d = ImageDraw.Draw(img)
            
            # تحديد مسار الخط بدقة
            base_path = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(base_path, "font.ttf")
            
            if os.path.exists(font_path):
                # تكبير الخطوط لتناسب دقة الصور في X
                font_title = ImageFont.truetype(font_path, 55)
                font_body = ImageFont.truetype(font_path, 34)
                logging.info("✅ Cairo font loaded from font.ttf")
            else:
                logging.error(f"❌ font.ttf not found at {font_path}. Checking root...")
                font_title = font_body = ImageFont.load_default()

            # رسم العنوان
            d.text((50, 40), "TECHAGENT INTEL | 2026", fill=(29, 155, 240), font=font_title)
            
            # رسم الأسطر مع مسافات مريحة للعين
            y_offset = 180
            for line in content.split('\n'):
                if line.strip():
                    # محاذاة النص وتعديله
                    d.text((50, y_offset), line.strip(), fill=(235, 240, 245), font=font_body)
                    y_offset += 60
            
            img_name = "verified_tech_card.png"
            img.save(img_name)
            return img_name
        except Exception as e:
            logging.error(f"Rendering Error: {e}")
            return None

    def _generate_content(self, topic):
        # السياسة التحريرية المعتمدة
        prompt = (
            f"أنت TechAgent. قدم 5 نقاط تقنية جافة وعميقة جداً للشباب المحترفين حول: {topic}. "
            "ممنوع استخدام Markdown. ممنوع المقدمات. الختم بـ +#."
        )
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Generation Error: {e}")
            return None

    def run(self):
        topics = [
            "مستقبل البرمجة مع Cursor و AI Agents",
            "ثورات معالجات 2026: Snapdragon vs Apple",
            "أدوات AI لتوليد الدخل السلبي للشباب التقني"
        ]
        selected_topic = random.choice(topics)
        content = self._generate_content(selected_topic)
        
        if content:
            path = self._create_visual_card(content)
            if path:
                try:
                    media = self.api_v1.media_upload(path)
                    tweet_text = f"🚨 جديد TechAgent: {selected_topic}\n\nتحليل عتاد وبرمجيات جيل المحترفين. 👇\n\n+#"
                    self.client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
                    logging.info("🚀 Tweet with Image posted successfully!")
                except Exception as e:
                    logging.error(f"X Posting Error: {e}")

if __name__ == "__main__":
    TechAgentUltimate().run()
