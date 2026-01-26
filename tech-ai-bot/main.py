import os
import logging
import tweepy
from openai import OpenAI
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    logging.error("Pillow is not installed. Run: pip install Pillow")

import random
import time

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v37.0 [Final Trend-Magnet] ===")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # إعداد X (Premium Support)
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
            "اسمك TechAgent. وكيل تقني لجيل الشباب. النشر الاستهدافي والردود الذكية. "
            "المواضيع: (AI العمل الحر، عتاد الألعاب، تسريبات الهواتف، الأمن السيبراني، الفضاء، البرمجة، Crypto). "
            "القواعد: لغة تقنية جافة، بدون لمسات لغوية، الختم بـ +#. "
            "في المقارنات: استخدم نقاط واضحة ومباشرة فقط."
        )

    def _create_visual_card(self, content):
        """توليد البطاقة البصرية لضمان التنظيم (المقترح 2)"""
        try:
            # حجم يناسب X
            img = Image.new('RGB', (1000, 750), color=(13, 17, 23)) 
            d = ImageDraw.Draw(img)
            
            # نص العنوان
            d.text((50, 40), "TECHAGENT INTEL | 2026", fill=(29, 155, 240))
            # محتوى التقرير
            d.text((50, 110), content, fill=(230, 237, 243))
            
            path = "tech_trend_card.png"
            img.save(path)
            return path
        except Exception as e:
            logging.error(f"Image Creation Failed: {e}")
            return None

    def _generate_ai_content(self, prompt, is_visual=False):
        try:
            prefix = "صغ تقريراً تقنياً مكثفاً بنقاط واضحة لبطاقة بصرية حول: " if is_visual else ""
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": f"{prefix}{prompt}"}],
                temperature=0.3
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _process_mentions(self):
        """الردود الذكية (ركيزة أساسية)"""
        try:
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            if mentions.data:
                for tweet in mentions.data:
                    reply = self._generate_ai_content(f"رد تقني جاف: {tweet.text}")
                    if reply:
                        if "+#" not in reply: reply += "\n+#"
                        self.client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                        time.sleep(5)
        except Exception:
            logging.info("Mentions limit reached.")

    def _publish_targeted_trend(self):
        """نشر المواضيع الجاذبة للشباب والتريندات"""
        scenarios = [
            "مقارنة تسريبات معالجات iPhone 18 Pro و Samsung S26 Ultra",
            "أدوات Cursor و GitHub Copilot: هل انتهى عصر المبرمج التقليدي؟",
            "أفضل كروت شاشة RTX 5080/5090 لتعدين الـ AI والألعاب",
            "ثغرات الأمن السيبراني في تطبيقات التواصل 2026 وكيفية الحماية",
            "إنترنت Starlink المباشر للهواتف: هل ستختفي شركات الاتصال؟"
        ]
        topic = random.choice(scenarios)
        content = self._generate_ai_content(topic, is_visual=True)
        
        if content:
            img_path = self._create_visual_card(content)
            if img_path:
                try:
                    media = self.api_v1.media_upload(img_path)
                    status = f"📊 تقرير التقنية اليومي: {topic.split(':')[0]}\n\nتحليل معمق لجيل المحترفين. 👇\n\n+#"
                    self.client_v2.create_tweet(text=status, media_ids=[media.media_id])
                    logging.info("🚀 Published Trend Post with Image.")
                except Exception as e:
                    logging.error(f"X Post Error: {e}")

    def run(self):
        self._publish_targeted_trend()
        self._process_mentions()

if __name__ == "__main__":
    TechAgentUltimate().run()
