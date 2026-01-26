import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import random
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v38.0 [Arabic Visual Support] ===")
        
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
            "اسمك TechAgent. وكيل تقني لجيل الشباب. النشر الاستهدافي والردود الذكية. "
            "المواضيع: (AI العمل الحر، عتاد الألعاب، تسريبات الهواتف، الأمن السيبراني، الفضاء، البرمجة). "
            "القواعد: لغة تقنية جافة، بدون لمسات لغوية، الختم بـ +#. "
            "في المقارنات: استخدم نقاطاً قصيرة جداً ومباشرة."
        )

    def _create_visual_card(self, content):
        """توليد بطاقة بصرية تدعم العربية"""
        try:
            img = Image.new('RGB', (1000, 800), color=(13, 17, 23))
            d = ImageDraw.Draw(img)
            
            # تحديد مسار ملف الخط (تأكد من رفعه للمستودع باسم font.ttf)
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            
            if os.path.exists(font_path):
                font_title = ImageFont.truetype(font_path, 45)
                font_body = ImageFont.truetype(font_path, 30)
            else:
                logging.warning("Font file not found, using default.")
                font_title = font_body = ImageFont.load_default()

            # رسم النصوص (مع مراعاة الهوامش)
            d.text((50, 50), "TECHAGENT INTEL | 2026", fill=(29, 155, 240), font=font_title)
            
            # تقسيم النص الطويل لأسطر لضمان بقائه داخل الصورة
            y_position = 150
            for line in content.split('\n'):
                d.text((50, y_position), line, fill=(230, 237, 243), font=font_body)
                y_position += 45
            
            path = "tech_trend_card.png"
            img.save(path)
            return path
        except Exception as e:
            logging.error(f"Image Creation Failed: {e}")
            return None

    def _generate_ai_content(self, prompt, is_visual=False):
        try:
            prefix = "اكتب 5 نقاط تقنية مكثفة جداً حول: " if is_visual else ""
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

    def _publish_trend_post(self):
        scenarios = [
            "تسريبات عتاد iPhone 18 Pro و Samsung S26 Ultra",
            "مستقبل البرمجة مع Cursor و AI Agents",
            "أداء كروت الشاشة RTX 50-series في الألعاب الثقيلة",
            "أدوات AI للعمل الحر لزيادة الدخل 2026",
            "تأمين البيانات الشخصية من هجمات الـ AI المتطورة"
        ]
        topic = random.choice(scenarios)
        content = self._generate_ai_content(topic, is_visual=True)
        
        if content:
            img_path = self._create_visual_card(content)
            if img_path:
                try:
                    media = self.api_v1.media_upload(img_path)
                    status = f"📊 تقرير التقنية اليومي: {topic}\n\nتحليل منظم لجيل المحترفين الجدد. 👇\n\n+#"
                    self.client_v2.create_tweet(text=status, media_ids=[media.media_id])
                    logging.info("🚀 Published Trend Post with Image.")
                except Exception as e:
                    logging.error(f"X Post Error: {e}")

    def run(self):
        self._publish_trend_post()
        self._process_mentions()

if __name__ == "__main__":
    TechAgentUltimate().run()
