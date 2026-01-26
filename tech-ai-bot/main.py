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
        logging.info("=== TechAgent Pro v45.0 [High-Value Content Edition] ===")
        
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
            "أنت TechAgent. خبير تقني لجيل المحترفين. لغتك جافة، غنية بالأرقام، وخالية من الحشو. "
            "الهدف: إثراء القارئ بمعلومات غير شائعة حول: (هندسة البرمجيات، عتاد الـ AI، خوارزميات المنصات، "
            "أدوات الإنتاجية، الأمن السيبراني العميق، واقتصاد التقنية). "
            "القواعد: الختم دائماً بـ +#. التنسيق: نقاط مركزة."
        )

    def _create_visual_card(self, content):
        try:
            img = Image.new('RGB', (1200, 1000), color=(5, 10, 15))
            d = ImageDraw.Draw(img)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(current_dir, "font.ttf")
            
            if os.path.exists(font_path):
                font_title = ImageFont.truetype(font_path, 65)
                font_body = ImageFont.truetype(font_path, 38)
            else:
                font_title = font_body = ImageFont.load_default()

            d.text((70, 60), "TECHAGENT INTEL REPORT | 2026", fill=(29, 155, 240), font=font_title)
            
            y_pos = 220
            for line in content.split('\n'):
                if line.strip():
                    d.text((70, y_pos), line.strip(), fill=(245, 245, 245), font=font_body)
                    y_pos += 70
            
            path = "tech_report.png"
            img.save(path)
            return path
        except Exception as e:
            logging.error(f"Rendering Error: {e}")
            return None

    def _publish_enriched_post(self):
        # مصفوفة المحتوى المنوع والمثري
        categories = {
            "AI & Future": [
                "تحليل الفرق التقني بين نماذج Transformer و نماذج SSM القادمة",
                "أدوات AI لبرمجة تطبيقات الـ Full-stack في دقائق",
                "هندسة الأوامر (Chain-of-Thought) للحصول على نتائج برمجية دقيقة"
            ],
            "Social Engineering": [
                "كيف تعمل خوارزمية التوصية في YouTube لعام 2026؟",
                "تحليل الـ Metadata وكيف تستخدمها المنصات لتصنيف المحتوى",
                "استراتيجيات الـ SEO الحديثة داخل منصات التواصل الاجتماعي"
            ],
            "Hardware & Tech": [
                "مقارنة بين معمارية x86 و ARM في أجهزة الـ Server لعام 2026",
                "لماذا نحتاج الـ NPUs في الأجهزة المحمولة؟ تحليل الأداء",
                "تسريبات تقنيات الشحن السريع 300W+ وتأثيرها على عمر البطارية"
            ],
            "Cyber Security": [
                "تحليل هجمات الـ Zero-day المعتمدة على الـ AI",
                "بروتوكولات التشفير ما بعد الكوانتم (Post-Quantum Cryptography)",
                "طرق تأمين المحافظ الرقمية (Cold Wallets) من الاختراقات الحديثة"
            ]
        }
        
        cat_name = random.choice(list(categories.keys()))
        topic = random.choice(categories[cat_name])
        
        prompt = f"قدم تحليلاً تقنياً عميقاً ومثرياً (5 نقاط بالبيانات) حول: {topic}. اجعل المعلومات حصرية للمحترفين."
        
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
                temperature=0.3
            )
            content = resp.choices[0].message.content.strip()
            
            img_path = self._create_visual_card(content)
            if img_path:
                media = self.api_v1.media_upload(img_path)
                status = f"📊 [{cat_name}] {topic}\n\nتحليل معمق لجيل التقنيين الجدد. 👇\n\n+#"
                self.client_v2.create_tweet(text=status, media_ids=[media.media_id])
                logging.info(f"🚀 Published: {topic}")
        except Exception as e:
            logging.error(f"Post Error: {e}")

    def run(self):
        self._publish_enriched_post()

if __name__ == "__main__":
    TechAgentUltimate().run()
