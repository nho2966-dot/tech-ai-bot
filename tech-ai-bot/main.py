import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time

# نظام حماية استيراد المكتبات لضمان التشغيل المستمر
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False
    logging.warning("⚠️ مكتبات RTL مفقودة! سيتم استخدام النص الخام.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v71.0 [Fixed & Stable] ===")
        
        # إعداد المحرك الذكي والاتصال بـ X
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

        # ضبط نبرة الصوت: خبير، سلس، ويدمج المصطلحات الإنجليزية
        self.system_instr = (
            "أنت TechAgent. وكيل تقني محترف بأسلوب سلس وممتع. "
            "قاعدتك: استخدم المصطلحات التقنية بالإنجليزية (Technical Terms) "
            "مع ذكر تعريبها أو شرحها العربي في السياق. "
            "مثال: 'خوارزميات التعلم العميق (Deep Learning)'. "
            "الأسلوب: تفاعلي، ذكي، غير جاف. الختم دائماً بـ +#. "
            "المحتوى: تقنيات 2026، AI، هاردوير، وسيو المنصات."
        )

    def _fix_text(self, text):
        """معالجة النص العربي لليمين إلى اليسار"""
        if AR_SUPPORT:
            return get_display(arabic_reshaper.reshape(text))
        return text

    def _create_visual(self, content):
        """توليد صورة احترافية مع هوامش أمان 100px ومحاذاة يمين"""
        try:
            width, height = 1200, 1000
            padding = 100
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            
            font_path = os.path.join(os.path.dirname(__file__), "font.ttf")
            font = ImageFont.truetype(font_path, 38) if os.path.exists(font_path) else ImageFont.load_default()
            font_bold = ImageFont.truetype(font_path, 55) if os.path.exists(font_path) else ImageFont.load_default()

            title = self._fix_text("تقرير TechAgent التقني")
            d.text((width - padding, 60), title, fill=(56, 189, 248), font=font_bold, anchor="ra")
            
            y_pos = 220
            for line in content.split('\n'):
                if not line.strip(): continue
                wrapped = textwrap.wrap(line, width=50)
                for w_line in wrapped:
                    d.text((width - padding, y_pos), self._fix_text(w_line.strip()), fill=(241, 245, 249), font=font, anchor="ra")
                    y_pos += 65
            
            path = "tech_output.png"
            img.crop((0, 0, width, min(y_pos + 100, height))).save(path)
            return path
        except Exception as e:
            logging.error(f"Image Visual Error: {e}")
            return None

    def _get_ai_text(self, prompt):
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
                temperature=0.6
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Fetch Error: {e}")
            return None

    def _interact(self):
        """الردود الذكية وصيد الكلمات المفتاحية"""
        try:
            me = self.client_v2.get_me().data
            mentions = self.client_v2.get_users_mentions(id=me.id, max_results=5)
            if mentions and mentions.data:
                for tweet in mentions.data:
                    reply = self._get_ai_text(f"رد بأسلوب خبير وسلس ومصطلحات مزدوجة على: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
            
            keywords = ["أفضل معالج 2026", "مستقبل الذكاء الاصطناعي"]
            query = f"({ ' OR '.join(keywords) }) -is:retweet lang:ar"
            search = self.client_v2.search_recent_tweets(query=query, max_results=2)
            if search and search.data:
                for tweet in search.data:
                    reply = self._get_ai_text(f"شارك نصيحة تقنية سلسة جداً مع هذا الشخص: {tweet.text}")
                    if reply:
                        self.client_v2.create_tweet(text=f"{reply}\n+#", in_reply_to_tweet_id=tweet.id)
                        time.sleep(15)
        except Exception as e:
            logging.error(f"Interaction Task Error: {e}")

    def _post(self):
        """دورة النشر الآلي"""
        scenarios = [
            ("أهمية وحدات المعالجة العصبية (NPUs) في جوالات 2026", False),
            ("مقارنة بين RTX 5090 و RTX 4090 من حيث كفاءة الطاقة (Power Efficiency)", True),
            ("كيف تختار مزود الطاقة (PSU) المناسب لتجميعتك؟", False)
        ]
        topic, is_img = random.choice(scenarios)
        content = self._get_ai_text(f"اكتب محتوى ممتع عن {topic}")
        
        if content:
            tags = "#تقنية #ذكاء_اصطناعي #TechAgent"
            if is_img:
                path = self._create_visual(content)
                if path:
                    media = self.api_v1.media_upload(path)
                    self.client_v2.create_tweet(text=f"🚀 {topic}\n\nتحليلنا الكامل في الصورة! 👇\n\n{tags}\n\n+#", media_ids=[media.media_id])
            else:
                self.client_v2.create_tweet(
