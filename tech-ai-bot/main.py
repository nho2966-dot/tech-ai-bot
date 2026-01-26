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

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v65.0 [The Smooth & Friendly Edition] ===")
        
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

        # تغيير التعليمات لتصبح "سلسة" و"ودودة"
        self.system_instr = (
            "أنت TechAgent. صديق تقني خبير وسلس جداً في أسلوبك. "
            "تحدث ببساطة واحترافية (لغة بيضاء تقنية). ابتعد عن الجمود والجفاف. "
            "اجعل القارئ يشعر بالحماس للمعلومة. الختم دائماً بـ +#. "
            "المحتوى: AI، سيو المنصات، عتاد، وتسريبات."
        )

    def _prepare_arabic_text(self, text):
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)

    def _create_safe_visual_table(self, content):
        """صورة مقارنة بلمسة بصرية ناعمة ومحاذاة RTL"""
        try:
            width, height = 1200, 1000
            padding = 100
            line_height = 65
            # تغيير لون الخلفية ليكون أكثر عصرية (Dark Blue-Grey)
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()

            # عنوان جذاب
            title = self._prepare_arabic_text("نظرة تقنية: مقارنة شاملة")
            d.text((width - padding, 60), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            d.line([(padding, 145), (width - padding, 145)], fill=(51, 65, 85), width=3)
            
            y_pos = 220
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    clean_line = self._prepare_arabic_text(w_line.strip())
                    d.text((width - padding, y_pos), clean_line, fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += line_height
            
            footer = self._prepare_arabic_text("بكل حب، وحدة تحليل TechAgent")
            d.text((width - padding, y_pos + 60), footer, fill=(148, 163, 184), font=font, anchor="ra")
            
            final_img = img.crop((0, 0, width, min(y_pos + 150, height)))
            path = "smooth_report.png"
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
                temperature=0.7 # رفع الحرارة قليلاً ليكون الكلام أكثر إبداعاً وسلاسة
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _handle_interactions(self):
        try:
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            if mentions.data:
                for tweet in mentions.data:
                    reply = self._generate_ai_response(f"رد بأسلوب صديق تقني ذكي وسلس على: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
                        logging.info(f"✅ تم الرد بسلاسة على: {tweet.id}")

            keywords = ["أفضل جوال 2026", "تعلم الذكاء الاصطناعي", "مشكلة في الويندوز"]
            query = f"({ ' OR '.join(keywords) }) -is:retweet lang:ar"
            search = self.client_v2.search_recent_tweets(query=query, max_results=3)
            if search.data:
                for tweet in search.data:
                    reply = self._generate_ai_response(f"قدم نصيحة تقنية ذكية وسلسة لصاحب هذه التغريدة: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
                        logging.info(f"🎯 دردشة تقنية سلسة مع: {tweet.id}")
                        time.sleep(10)
        except Exception as e:
            logging.error(f"Interaction Error: {e}")

    def _publish_content(self):
        scenarios = [
            ("أدوات AI هتغير حياتك العملية في 2026", False),
            ("مقارنة سريعة: RTX 5090 و RTX 4090.. مين يستاهل؟", True),
            ("سر صغير في خوارزمية X يخلي تغريداتك تطير!", False),
            ("ليش معالج Apple القادم رح يكون ثورة؟", False)
        ]
        topic, is_comp = random.choice(scenarios)
        content = self._generate_ai_response(f"اكتب محتوى تقني سلس وممتع حول: {topic}")
        
        if content:
            hashtags = "#تقنية_ببساطة #ذكاء_اصطناعي #TechAgent"
            if is_comp:
                path = self._create_safe_visual_table(content)
                if path:
                    media = self.api_v1.media_upload(path)
                    text = f"🚨 {topic}\n\nجهّزت لك هالمقارنة عشان تختار الأنسب لك! 🚀\n\n{hashtags}\n\n+#"
                    self.client_v2.create_tweet(text=text, media_ids=[media.media_id])
            else:
                text = f"🚀 {topic}\n\n{content}\n\n💡 لو عندك أي استفسار، أنا موجود بالتعليقات! 👇\n\n{hashtags}"
                self.client_v2.create_tweet(text=text)
            logging.info(f"🚀 Published smoothly: {topic}")

    def run(self):
        self._publish_content()
        time.sleep(20)
        self._handle_interactions()

if __name__ == "__main__":
    TechAgentUltimate().run()
