import os
import logging
import tweepy
from openai import OpenAI
from datetime import datetime
import random
import time
import hashlib

# إعداد السجل بنبرة احترافية ولطيفة
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgent:
    def __init__(self):
        logging.info("=== TechAgent Pro v21.0 [Youth & Trends Edition] ===")
        
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # الدستور المحدث لاستقطاب فئة الشباب التقني
        self.system_instr = (
            "اسمك TechAgent. أنت وكيل ذكي يستهدف الشباب التقني الطموح على X. "
            "مهمتك تقديم محتوى جذاب، سريع، وعالي القيمة يركز على: "
            "1. (Lifestyle Tech): كيف يغير AI حياتهم اليومية، دراستهم، وعملهم. "
            "2. (Gaming & Gear): أحدث عتاد الألعاب، مقارنات كروت الشاشة، وتحديثات GTA/Fortnite. "
            "3. (Smartphones): مقارنات حادة بـ Markdown بين iPhone و Samsung و أجهزة الألعاب المحمولة. "
            "4. (Digital Wealth): تسريبات العملات الرقمية والتقنيات المالية الناشئة. "
            "القواعد: لغة تقنية جافة ومباشرة، جداول واضحة، روابط مصادر موثوقة، والختم بـ +#."
        )

    def _generate_youth_content(self, niche):
        # محاور تهم الشباب بناءً على تحليلات X
        prompts = {
            "gaming": "حلل أحدث تسريب لـ GTA VI أو تحديث رئيسي في Fortnite، مع جدول لمواصفات التشغيل المطلوبة ورابط.",
            "ai_productivity": "انشر عن أداة AI جديدة تمكن الشباب من زيادة دخلهم أو إنتاجيتهم (مثل أدوات توليد الفيديو أو الكود) مع الرابط.",
            "phone_wars": "مقارنة تقنية جافة بجدول Markdown بين iPhone 17 و Samsung S25 من منظور مستخدم شاب (ألعاب، تصوير، بطارية).",
            "leaks": "انشر أحدث تسريبات Mark Gurman حول أجهزة Apple القادمة بأسلوب مشوق ومباشر مع ذكر الرابط."
        }
        
        try:
            resp = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": self.system_instr},
                    {"role": "user", "content": prompts[niche]}
                ],
                temperature=0.3,
                max_tokens=1200
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error: {e}")
            return None

    def _is_duplicate(self, content):
        h = hashlib.md5(content.encode()).hexdigest()
        if os.path.exists(LAST_TWEET_FILE):
            with open(LAST_TWEET_FILE, "r") as f:
                if h in f.read(): return True
        return False

    def _save_hash(self, content):
        h = hashlib.md5(content.encode()).hexdigest()
        with open(LAST_TWEET_FILE, "a") as f:
            f.write(f"{h}|{datetime.now().isoformat()}\n")

    def run(self):
        # اختيار المحور الشبابي عشوائياً
        niche = random.choice(["gaming", "ai_productivity", "phone_wars", "leaks"])
        logging.info(f"TechAgent يستهدف اهتمامات الشباب في: {niche}")
        
        content = self._generate_youth_content(niche)
        
        if content and not self._is_duplicate(content):
            if "+#" not in content: content += "\n+#"
            try:
                self.x_client.create_tweet(text=content)
                self._save_hash(content)
                logging.info(f"🚀 تم نشر المحتوى الشبابي بنجاح.")
            except Exception as e:
                logging.error(f"X Error: {e}")

if __name__ == "__main__":
    TechAgent().run()
