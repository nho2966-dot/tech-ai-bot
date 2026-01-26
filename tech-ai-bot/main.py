import os
import logging
import tweepy
import random
import time
import json
from openai import OpenAI
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentPro:
    def __init__(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.history_file = "tweet_history.json"

    def _is_duplicate(self, content):
        """التحقق من أن التغريدة لم تُنشر من قبل (بناءً على تشابه المعنى)"""
        if not os.path.exists(self.history_file):
            return False
        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
            # التحقق من آخر 50 تغريدة لضمان التنوع
            return any(content[:30] in old_tweet for old_tweet in history[-50:])

    def _save_to_history(self, content):
        history = []
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        history.append(content)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history[-100:], f, ensure_ascii=False) # الاحتفاظ بآخر 100 فقط

    def ask_ai(self, prompt, system_instruction):
        engines = [
            {"name": "Qwen", "url": "https://openrouter.ai/api/v1", "key": self.openrouter_key, "model": "alibabacloud/qwen-2.5-72b-instruct"},
            {"name": "OpenAI", "url": None, "key": self.openai_key, "model": "gpt-4o-mini"}
        ]
        
        for engine in engines:
            if engine["key"]:
                try:
                    client = OpenAI(base_url=engine["url"], api_key=engine["key"]) if engine["url"] else OpenAI(api_key=engine["key"])
                    resp = client.chat.completions.create(
                        model=engine["model"],
                        messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                        max_tokens=400
                    )
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    logging.warning(f"فشل محرك {engine['name']}: {e}")
        return None

    def run(self):
        try:
            # 1. تحديد الوقت الحالي لإجبار الـ AI على محتوى "جديد جداً"
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # 2. بناء أمر (Prompt) يركز على العامل الزمني والتسريبات الحديثة
            instruction = f"""أنت رادار تقني عالمي. اليوم هو {current_date}.
            وظيفتك: تقديم أحدث تسريب أو خبر تقني عاجل وقع في الـ 48 ساعة الأخيرة فقط.
            ركز على عمالقة التقنية (Apple, Nvidia, Samsung, Google).
            القواعد:
            - ممنوع تكرار أخبار قديمة.
            - يجب أن يكون المحتوى مفهوماً ومكتملاً بنسبة 100%.
            - اللغة العربية فصحى واحترافية.
            - الطول أقل من 275 حرفاً."""

            prompt = "أعطني أهم تسريب تقني أو خبر عاجل ومؤكد لهذا اليوم. ابدأ التغريدة بكلمة '🚨 جديد' أو '🚨 تسريب عاجل'."
            
            # 3. محاولات توليد محتوى غير مكرر
            for _ in range(3): # 3 محاولات للحصول على نص فريد
                raw_content = self.ask_ai(prompt, instruction)
                if raw_content and not self._is_duplicate(raw_content):
                    # نشر التغريدة
                    self.x_client.create_tweet(text=raw_content)
                    self._save_to_history(raw_content)
                    logging.info(f"✨ تم النشر (محتوى جديد وفريد): {raw_content[:50]}")
                    break
                else:
                    logging.info("المحتوى مكرر أو غير كافٍ، إعادة التوليد...")

        except Exception as e:
            logging.error(f"خطأ: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
