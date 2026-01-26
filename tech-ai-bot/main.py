import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw
import random
import time

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v36.0 [Trend-Magnet Edition] ===")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # إعداد X (دعم Premium لرفع الوسائط)
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
            "اسمك TechAgent. وكيل تقني لجيل الشباب. "
            "مهمتك: النشر الاستهدافي والردود الذكية. "
            "المواضيع: (AI للعمل الحر، عتاد الألعاب، تسريبات الهواتف، الأمن السيبراني، الإنترنت الفضائي، البرمجة بالذكاء الاصطناعي). "
            "القواعد: لغة تقنية جافة، لا تستخدم جداول Markdown في النص، بل نقاط واضحة ومباشرة. الختم بـ +#."
        )

    def _create_visual_card(self, content):
        """تحويل المحتوى لبطاقة بصرية احترافية (المقترح 2)"""
        try:
            img = Image.new('RGB', (1000, 700), color=(10, 10, 12)) 
            d = ImageDraw.Draw(img)
            # رسم ترويسة البطاقة
            d.text((50, 40), "TECHAGENT INSIGHTS | 2026", fill=(29, 155, 240))
            d.text((50, 120), content, fill=(240, 240, 240))
            
            path = "trend_card.png"
            img.save(path)
            return path
        except Exception as e:
            logging.error(f"Visual Card Error: {e}")
            return None

    def _generate_content(self, prompt, is_visual=False):
        try:
            prefix = "صغ محتوى تقني مكثف بنقاط لبطاقة بصرية عن: " if is_visual else ""
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
        """الردود الذكية (شرط ثابت)"""
        try:
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            if mentions.data:
                for tweet in mentions.data:
                    reply = self._generate_content(f"رد تقني جاف على: {tweet.text}")
                    if reply:
                        if "+#" not in reply: reply += "\n+#"
                        self.client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                        time.sleep(3)
        except Exception:
            logging.info("Mentions limit or no new tweets.")

    def _publish_trend_post(self):
        """النشر الاستهدافي للمواضيع الجاذبة للشباب"""
        scenarios = [
            "أفضل أدوات البرمجة بالذكاء الاصطناعي (Cursor vs VS Code) لعام 2026",
            "مقارنة تسريبات مواصفات iPhone 18 و Samsung S26 Ultra",
            "كيفية تأمين حساباتك من هجمات الهندسة الاجتماعية المتطورة",
            "تأثير الإنترنت الفضائي (Starlink) على مستقبل العمل الحر في المناطق النائية",
            "أحدث كروت الشاشة (RTX 50-series) وأدائها مع ألعاب الـ 4K"
        ]
        topic = random.choice(scenarios)
        content = self._generate_content(topic, is_visual=True)
        
        if content:
            img_path = self._create_visual_card(content)
            try:
                media = self.api_v1.media_upload(img_path)
                status_text = f"🚨 تحليل تقني جديد: {topic.split('(')[0]}\n\nالتفاصيل الكاملة في البطاقة المرفقة لجيل المحترفين. 👇\n\n+#"
                self.client_v2.create_tweet(text=status_text, media_ids=[media.media_id])
                logging.info("🚀 تم نشر محتوى التريند بنجاح.")
            except Exception as e:
                logging.error(f"Post Error: {e}")

    def run(self):
        self._publish_trend_post()
        self._process_mentions()

if __name__ == "__main__":
    TechAgentUltimate().run()
