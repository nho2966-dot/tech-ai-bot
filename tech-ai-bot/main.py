import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time

# إعداد السجل التقني
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v56.0 [Final Syntax Fix] ===")
        
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
            "اسمك TechAgent. وكيل تقني جاف. الختم دائماً بـ +#. "
            "المحتوى غني بالبيانات والأرقام. المصدر: TechAgent Intelligence."
        )

    def _create_safe_visual_table(self, content):
        try:
            width, height = 1200, 1000
            padding = 100
            line_height = 60
            img = Image.new('RGB', (width, height), color=(8, 12, 18))
            d = ImageDraw.Draw(img)
            
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()

            d.text((padding, 60), "TECHAGENT | INTEL REPORT", fill=(29, 155, 240), font=font_bold)
            d.line([(padding, 140), (width-padding, 140)], fill=(40, 50, 60), width=2)
            
            y_pos = 200
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    d.text((padding, y_pos), w_line.strip(), fill=(230, 235, 240), font=font)
                    y_pos += line_height
            
            d.text((padding, y_pos + 40), "Source: TechAgent Intelligence Unit", fill=(70, 80, 90), font=font)
            final_img = img.crop((0, 0, width, min(y_pos + 150, height)))
            path = "intel_table.png"
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
                temperature=0.2
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
                    reply = self._generate_ai_response(f"رد تقني جاف ومختصر: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
                        logging.info(f"✅ تم الرد على المنشن: {tweet.id}")

            keywords = ["RTX 5090", "تسريبات آيفون", "أدوات AI للبرمجة"]
            query = f"({ ' OR '.join(keywords) }) -is:retweet lang:ar"
            search = self.client_v2.search_recent_tweets(query=query, max_results=3)
            if search.data:
                for tweet in search.data:
                    reply = self._generate_ai_response(f"حلل هذه التغريدة تقنياً باختصار: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
                        logging.info(f"🎯 تم صيد تفاعل جديد: {tweet.id}")
                        time.sleep(10)
        except Exception as e:
            logging.error(f"Interaction Error: {e}")

    def _publish_content(self):
        scenarios = [
            ("مقارنة عتادية: RTX 5090 vs RTX 4090", True),
            ("خوارزمية X: تحليل هندسي لزيادة الوصول", False),
            ("مقارنة معالجات: Snapdragon 8 Gen 5 vs Apple A19", True),
            ("أدوات AI لزيادة إنتاجية المبرمجين 2026", False)
        ]
        topic, is_comp = random.choice(scenarios)
        content = self._generate_ai_response(f"حلل تقنياً: {topic}. {'اجعلها مقارنة بجدول' if is_comp else '5 نقاط مكثفة'}")
        
        if content:
            hashtags = "#الذكاء_الاصطناعي #تقنية #برمجة #TechAgent"
            source = "المصدر: وحدة تحليل البيانات - TechAgent"
            
            if is_comp:  # تم إضافة النقطتين هنا للإصلاح
                path = self._create_safe_visual_table(content)
                if path:
                    media = self.api_v1.media_upload(path)
                    text = f"🚨 {topic}\n\nبيانات المقارنة المرفقة دقيقة.\n\n{source}\n\n{hashtags}\n\n+#"
                    self.client_v2.create_tweet(text=text, media_ids=[media.media_id])
            else:
                text = f"🚨 {topic}\n\n{content}\n\n💡 ضع استفسارك في التعليقات للتحليل الآلي.\n\n{source}\n\n{hashtags}"
                self.client_v2.create_tweet(text=text)
            logging.info(f"🚀 Published: {topic}")

    def run(self):
        self._publish_content()
        time.sleep(30)
        self._handle_interactions()

if __name__ == "__main__":
    TechAgentUltimate().run()
