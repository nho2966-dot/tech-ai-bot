import os
import logging
import tweepy
from openai import OpenAI
from datetime import datetime
import random
import time
import hashlib

# إعداد السجل التقني
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgent:
    def __init__(self):
        # إعداد العملاء
        router_key = os.getenv("OPENROUTER_API_KEY")
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1" if router_key else None,
            api_key=router_key or os.getenv("OPENAI_API_KEY")
        )
        self.model = "qwen/qwen-2.5-72b-instruct" if router_key else "gpt-4o-mini"
        
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # الدستور الصارم للوكيل TechAgent
        self.system_instr = (
            "اسمك TechAgent. وكيل تقني مختص. "
            "المجالات: AI، أمن سيبراني، ألعاب، تسريبات، وأجهزة. "
            "المصادر: TechCrunch, Wired, The Verge, BleepingComputer, NIST, المدونات الرسمية. "
            "القواعد: لغة تقنية جافة تماماً، بدون لمسات لغوية، استخدام جداول Markdown، ذكر الروابط، والختم بـ +#. "
            "إذا كان الخبر غير مؤكد، اذكر ذلك صراحة."
        )

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

    def _generate_content(self, user_msg):
        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_instr},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.2 # دقة عالية جداً
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def _process_mentions(self):
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, max_results=5)
            if not mentions.data: return

            for tweet in mentions.data:
                reply = self._generate_content(f"رد بذكاء وموضوعية على استفسار المتابع: {tweet.text}")
                if reply and not self._is_duplicate(reply):
                    if "+#" not in reply: reply += "\n+#"
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    self._save_hash(reply)
                    time.sleep(30)
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def _publish_daily(self):
        tasks = [
            "حلل أحدث ثغرة أمنية اليوم من NIST أو BleepingComputer مع الرابط.",
            "قدم مقارنة تقنية بجدول Markdown بين iPhone 17 و Samsung S25 بناءً على التسريبات.",
            "ما هي آخر تحديثات AI في الطب أو التعليم لعام 2026؟",
            "انقل سبقاً صحفياً تقنياً من Mark Gurman أو The Verge مع الرابط."
        ]
        content = self._generate_content(random.choice(tasks))
        if content and not self._is_duplicate(content) and len(content) <= 280:
            if "+#" not in content: content += "\n+#"
            self.x_client.create_tweet(text=content)
            self._save_hash(content)

    def run(self):
        self._process_mentions()
        self._publish_daily()

if __name__ == "__main__":
    TechAgent().run()
