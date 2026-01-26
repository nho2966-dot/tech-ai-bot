import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time
from bidi.algorithm import get_display
import arabic_reshaper

# إعداد السجل التقني
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v68.0 [Smooth, RTL & Stable] ===")
        
        # إعداد AI
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

        # نبرة صوت سلسة، خبيرة، وودودة
        self.system_instr = (
            "أنت TechAgent. خبير تقني بأسلوب سلس وممتع جداً. "
            "تجنب الجفاف، استخدم لغة بيضاء احترافية تشجع على القراءة. "
            "الختم دائماً بـ +#. ركز على عتاد 2026، الذكاء الاصطناعي، وتسريبات التقنية."
        )

    def _fix_rtl(self, text):
        """إصلاح اتجاه النص العربي ومعالجة الحروف المقطعة"""
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def _create_safe_visual_table(self, content):
        """توليد صورة احترافية: هوامش 100px + محاذاة يمين RTL"""
        try:
            width, height = 1200, 1000
            padding = 100
            line_height = 65
            img = Image.new('RGB', (width, height), color=(15, 23, 42)) # خلفية Dark Blue عصرية
            d = ImageDraw.Draw(img)
            
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()

            # رسم العنوان بمحاذاة يمين (anchor="ra")
            title = self._fix_rtl("نظرة تقنية: مقارنة الأداء")
            d.text((width - padding, 60), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            d.line([(padding, 145), (width - padding, 145)], fill=(51, 65, 85), width=3)
            
            y_pos = 220
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    # رسم النص من اليمين تماماً لضمان عدم الاقتطاع
                    d.text((width - padding, y_pos), self._fix_rtl(w_line.strip()), fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += line_height
                    if y_pos > height - padding: break
            
            footer = self._fix_rtl("المصدر: وحدة تحليل TechAgent")
            d.text((width - padding, y_pos + 60), footer, fill=(148, 163, 184), font=font, anchor="ra")
            
            final_img = img.crop((0, 0, width, min(y_pos + 150, height)))
            path = "tech_report_rtl.png"
            final_img.save(path)
            return path
        except Exception as e:
            logging.error(f"Image Error: {e}")
            return None

    def _generate_ai_response(self, prompt):
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _handle_interactions(self):
        """الردود الذكية وصيد التفاعل"""
        try:
            # 1. الرد على المنشن
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            if mentions and mentions.data:
                for tweet in mentions.data:
                    reply = self._generate_ai_response(f"رد بأسلوب صديق خبير وسلس على: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)

            # 2. صيد الكلمات المفتاحية
            keywords = ["أفضل كرت شاشة 2026", "تسريبات معالج Apple", "كيف أتعلم AI"]
            query = f"({ ' OR '.join(keywords) }) -is:retweet lang:ar"
            search = self.client_v2.search_recent_tweets(query=query, max_results=2)
            if search and search.data:
                for tweet in search.data:
                    reply = self._generate_ai_response(f"قدم نصيحة تقنية ذكية وسلسة جداً حول: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
                        time.sleep(10)
        except Exception as e:
            logging.error(f"Interaction Error: {e}")

    def _publish_cycle(self):
        """النشر الاستهدافي الدوري"""
        scenarios = [
            ("مقارنة RTX 5090 vs 4090: هل القفزة تسوى؟", True),
            ("3 أدوات AI هتختصر عليك ساعات من الشغل!", False),
            ("سر في إعدادات X يرفع وصول تغريداتك!", False),
            ("مقارنة Snapdragon 8 Gen 5 vs Apple A19 Pro", True)
        ]
        topic, is_comp = random.choice(scenarios)
        content = self._generate_ai_response(f"اكتب محتوى تقني ممتع وسلس عن: {topic}")
        
        if content:
            hashtags = "#تقنية #ذكاء_اصطناعي #TechAgent"
            if is_comp:
                path = self._create_safe_visual_table(content)
                if path:
                    media = self.api_v1.media_upload(path)
                    text = f"🚀 {topic}\n\nشوف هالمقارنة الحصرية وخبرني رأيك! 👇\n\n{hashtags}\n\n+#"
                    self.client_v2.create_tweet(text=text, media_ids=[media.media_id])
            else:
                text = f"💡 {topic}\n\n{content}\n\nأي سؤال؟ أنا بالتعليقات! 👇\n\n{hashtags}"
                self.client_v2.create_tweet(text=text)

    def run(self):
        self._publish_cycle()
        time.sleep(20)
        self._handle_interactions()

if __name__ == "__main__":
    TechAgentUltimate().run()
