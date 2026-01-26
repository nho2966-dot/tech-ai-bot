import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime, timedelta
import random
import time
import hashlib

# ─── إعداد السجل (Logs) ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgentPro:
    def __init__(self):
        logging.info("=== TechAgent Pro v6.2 – إصلاح الأخطاء البرمجية ===")
        
        self.config = self._load_config()

        # ─── إعداد الذكاء الاصطناعي ──────────────────────
        router_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if router_key:
            logging.info("تفعيل محرك OpenRouter (Qwen)")
            self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=router_key)
            self.model = "qwen/qwen-2.5-72b-instruct"
        elif openai_key:
            logging.info("تفعيل محرك OpenAI (Fallback)")
            self.ai_client = OpenAI(api_key=openai_key)
            self.model = "gpt-4o-mini"
        else:
            raise ValueError("❌ خطأ: لم يتم العثور على مفاتيح API (Secrets)")

        # ─── إعداد منصة X ──────────────────────────────────────────
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

    def _load_config(self):
        secret = os.getenv("CONFIG_YAML")
        if secret:
            try:
                return yaml.safe_load(secret)
            except:
                pass
        return {"behavior": {"daily_posts_target": 2}}

    def _was_similar_tweet_posted_today(self, content: str) -> bool:
        if not os.path.exists(LAST_TWEET_FILE):
            return False
        try:
            current_hash = hashlib.md5(content.encode()).hexdigest()
            with open(LAST_TWEET_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                        h, t = line.strip().split("|")
                        if datetime.now() - datetime.fromisoformat(t) < timedelta(hours=24):
                            if current_hash == h:
                                return True
        except:
            return False
        return False

    def _save_tweet_hash(self, content: str):
        h = hashlib.md5(content.encode()).hexdigest()
        with open(LAST_TWEET_FILE, "a", encoding="utf-8") as f:
            f.write(f"{h}|{datetime.now().isoformat()}\n")

    def _generate_future_tech_tweet(self):
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        التاريخ اليوم {today}. أنت خبير تقني متخصص في التسريبات.
        اكتب تغريدة احترافية بالعربية الفصحى عن (Apple أو Samsung أو Nvidia) وتوقعات 2026.
        ابدأ بـ '🚨 جديد:' أو '🔮 رادار المستقبل:'.
        يجب أن تكون التغريدة مكتملة المعنى، دقيقة، وأقل من 270 حرف.
        انهِ بسؤال تفاعلي.
        """
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"❌ خطأ AI: {e}")
            return None

    def run(self):
        try:
            me = self.x_client.get_me().data
            logging.info(f"✅ متصل بحساب: @{me.username}")
            
            content = self._generate_future_tech_tweet()
            if content and not self._was_similar_tweet_posted_today(content):
                self.x_client.create_tweet(text=content)
                self._save_tweet_hash(content)
                logging.info(f"🚀 تم النشر: {content[:50]}...")
            else:
                logging.info("⏭️ تخطي: محتوى مكرر أو غير صالح.")
        except Exception as e:
            logging.error(f"❌ خطأ في التشغيل: {e}")

if __name__ == "__main__":
    TechAgentPro().run()
