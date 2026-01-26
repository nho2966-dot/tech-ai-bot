import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time

# نظام حماية واستيراد مكتبات اللغة العربية (RTL)
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False
    logging.warning("⚠️ مكتبات RTL مفقودة! سيتم عرض النص بشكل مبسط.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v73.0 [Marketing & Engagement Mode] ===")
        
        # إعداد الاتصال بـ OpenRouter و X API
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

        # التعليمات البرمجية لنبرة الصوت (سلسة، تسويقية، وجدلية)
        self.system_instr = (
            "أنت TechAgent، خبير تقني وصانع محتوى مؤثر (Influencer). "
            "أسلوبك: ابدأ بـ Hook خاطف، استخدم المصطلحات التقنية بالإنجليزية مع تعريبها، "
            "واختم دائماً بسؤال جدلي يثير النقاش ويقسم الآراء. "
            "تحدث بلهجة بيضاء سلسة ومحفزة للتفاعل. الختم دائماً بـ +#."
        )

    def _fix_text(self, text):
        """تجهيز النص العربي للعرض الصحيح في الصور"""
        if AR_SUPPORT:
            return get_display(arabic_reshaper.reshape(text))
        return text

    def _create_visual(self, content):
        """إنشاء صورة احترافية مع إضافة المصدر"""
        try:
            width, height = 1200, 1100
            padding = 100
            img = Image.new('RGB', (width, height), color=(10, 15, 30))
            d = ImageDraw.Draw(img)
            
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()
            font_small = ImageFont.truetype(font_path, 28) if os.path.exists(font_path) else ImageFont.load_default()

            # رسم العنوان
            d.text((width - padding, 70), self._fix_text("تحليل TechAgent الحصري"), fill=(56, 189, 248), font=font_bold, anchor="ra")
            
            # رسم المحتوى
            y_pos = 220
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    d.text((width - padding, y_pos), self._fix_text(w_line.strip()), fill=(240, 240, 240), font=font, anchor="ra")
                    y_pos += 65
            
            # إضافة المصدر في أسفل الصورة
            source_tag = self._fix_text("المصدر: وحدة ذكاء TechAgent v73.0")
            d.text((width - padding, y_pos + 100), source_tag, fill=(100, 116, 139), font=font_small, anchor="ra")
            
            path = "tech_output.png"
            img.crop((0, 0, width, min(y_pos + 200, height))).save(path)
            return path
        except Exception as e:
            logging.error(f"Visual Creation Error: {e}")
            return None

    def _get_ai_text(self, prompt):
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Fetch Error: {e}")
            return None

    def _interact(self):
        """نظام الردود الذكية وتتبع الكلمات المفتاحية"""
        try:
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            if mentions and mentions.data:
                for tweet in mentions.data:
                    reply = self._get_ai_text(f"رد بأسلوب خبير وجدلي ومختصر على: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
        except Exception as e:
            logging.error(f"Interaction Task Error: {e}")

    def _post(self):
        """نظام النشر التسويقي بالمواضيع المعتمدة"""
        topics = [
            "وحدات المعالجة العصبية (NPUs) وهل بتنهي عصر الـ CPU؟",
            "مستقبل RTX 5090 وكفاءة الطاقة (Power Efficiency).",
            "صراع النظارات الذكية ضد الهواتف التقليدية في 2026.",
            "أدوات البرمجة بالذكاء الاصطناعي (AI Coding Tools) وهل بيفقد المبرمج وظيفته؟"
        ]
        topic = random.choice(topics)
        is_img = random.choice([True, False]) # تنويع بين النص والصور
        
        prompt = f"اكتب تغريدة تسويقية مثيرة ومحفزة جداً عن {topic}. استخدم مصطلحات إنجليزية وتعريبها، واختم بسؤال جدلي يثير النقاش بشدة."
        content = self._get_ai_text(prompt)
        
        if content:
            tags = "#تقنية #مستقبل #ذكاء_اصطناعي #TechAgent"
            if is_img:
                path = self._create_visual(content)
                if path:
                    media = self.api_v1.media_upload(path)
                    self.client_v2.create_tweet(
                        text=f"🔥 تحليل جديد من TechAgent\n\n(التفاصيل كاملة في الصورة المرفقة) 👇\n\n{tags}\n\n+#",
                        media_ids=[media.media_id]
                    )
            else:
                self.client_v2.create_tweet(text=f"{content}\n\n{tags}")

    def run(self):
        self._post()
        time.sleep(40) # انتظار بسيط قبل التفاعل
        self._interact()

if __name__ == "__main__":
    TechAgentUltimate().run()
