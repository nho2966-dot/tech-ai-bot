import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime, timedelta
import random
import time
import hashlib

# ─── إعداد السجل ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgentPro:
    def __init__(self):
        logging.info("=== TechAgent Pro v11.0 [The Specialist Master] ===")
        
        # ─── إعداد AI ──────────────────────────────────────────────────
        router_key = os.getenv("OPENROUTER_API_KEY")
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1" if router_key else None,
            api_key=router_key or os.getenv("OPENAI_API_KEY")
        )
        # استخدام موديل Qwen القوي جداً في العربية والتقنية
        self.model = "qwen/qwen-2.5-72b-instruct" if router_key else "gpt-4o-mini"

        # ─── إعداد منصة X ──────────────────────────────────────────
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def _generate_smart_content(self, system_msg, user_msg, temperature=0.75):
        """توليد محتوى فائق الذكاء مع مراعاة التخصص"""
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=temperature,
                max_tokens=350
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"خطأ في توليد المحتوى: {e}")
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

    def _process_mentions(self):
        """الرد الذكي جداً على المتابعين (خبير أمن وAI)"""
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, max_results=5, expansions=["author_id"])
            if not mentions.data: return

            system_instr = """أنت مرجع تقني عبقري. تخصصك: الذكاء الاصطناعي، الأمن السيبراني، والتوقعات المستقبلية.
            - ردودك ذكية، دقيقة تقنياً، ومختصرة.
            - إذا سُئلت عن أمن المعلومات، قدم نصيحة عملية وفورية.
            - استخدم العربية الفصحى الراقية."""

            for tweet in mentions.data:
                reply = self._generate_smart_content(system_instr, f"أجب بذكاء على: {tweet.text}")
                if reply and not self._is_duplicate(reply):
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    self._save_hash(reply)
                    logging.info(f"✅ تم الرد على منشن ذكي.")
                    time.sleep(random.randint(20, 40))
        except Exception as e:
            logging.error(f"خطأ في المنشنات: {e}")

    def _publish_specialized_tweet(self):
        """نشر محتوى يجمع بين السبق، الأمن، والـ AI"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # مصفوفة المواضيع المتفق عليها
        topics = [
            {
                "category": "AI & Future",
                "prompt": "اكتب عن أحدث ميزات الذكاء الاصطناعي الحالية (مثل نماذج التفكير Reasoning) وكيف ستتطور في 2027."
            },
            {
                "category": "CyberSecurity",
                "prompt": "حذر من ثغرة أمنية تقنية حديثة أو أسلوب هندسة اجتماعية متطور، واشرح كيفية الوقاية بأسلوب خبير."
            },
            {
                "category": "Tech Scoop",
                "prompt": "اكتب سبقاً صحفياً (تسريبات مؤكدة أو توقعات مبنية على بيانات) حول أجهزة Apple القادمة أو رقائق Nvidia."
            }
        ]
        
        chosen = random.choice(topics)
        system_instr = f"أنت رادار تقني عالمي. التاريخ: {today}. أنت مهتم جداً بالسبق والتحليل الأمني."
        
        content = self._generate_smart_content(system_instr, chosen["prompt"])
        
        if content and not self._is_duplicate(content):
            if len(content) <= 280:
                self.x_client.create_tweet(text=content)
                self._save_hash(content)
                logging.info(f"🚀 تم نشر تغريدة تخصصية: {chosen['category']}")

    def run(self):
        # 1. التفاعل الاجتماعي أولاً
        self._process_mentions()
        # 2. النشر التخصصي ثانياً
        self._publish_specialized_tweet()

if __name__ == "__main__":
    TechAgentPro().run()
