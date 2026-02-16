import os
import yaml
import sqlite3
import logging
import time
import feedparser
import tweepy
import random
from datetime import datetime, timedelta, timezone
from google import genai

# 1. الإعدادات واللوج
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("SovereignBot")

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

class SovereignBot:
    def __init__(self):
        self.db_path = config['bot']['database_path']
        self._init_db()
        self.gemini_key = os.getenv("GEMINI_KEY")
        self.sys_instruction = config['prompts']['system_core'].replace(
            "Industrial Revolution", "Artificial Intelligence and its latest tools"
        )
        # إعداد عملاء X (الإصدار 1.1 و 2.0)
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
        self.bot_id = self.client_v2.get_me().data.id

    def _init_db(self):
        if not os.path.exists(os.path.dirname(self.db_path)): os.makedirs(os.path.dirname(self.db_path))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def generate_ai_content(self, prompt_text):
        """توليد محتوى احترافي باستخدام Gemini"""
        try:
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_text,
                config={'system_instruction': self.sys_instruction}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ خطأ Gemini: {e}")
            return None

    def handle_replies(self):
        """الرد الذكي على الإشارات (Mentions)"""
        logger.info("📡 جاري فحص الإشارات (Mentions)...")
        try:
            mentions = self.client_v2.get_users_mentions(self.bot_id, expansions=['author_id'])
            if not mentions.data: return

            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT tweet_id FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone():
                        continue

                # توليد رد ذكي خليجي
                prompt = f"رد باختصار وذكاء بلهجة خليجية بيضاء على هذه التغريدة: {tweet.text}. ركز على أدوات AI و Google وانشر الفائدة للفرد."
                reply_text = self.generate_ai_content(prompt)

                if reply_text:
                    self.client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO replies (tweet_id) VALUES (?)", (str(tweet.id),))
                    logger.info(f"✅ تم الرد على التغريدة: {tweet.id}")
                    time.sleep(5) # لتجنب الـ Rate Limit
        except Exception as e:
            logger.error(f"❌ خطأ في الردود: {e}")

    def run_publisher(self):
        """النشر الاستهدافي للأخبار والأدوات"""
        gulf_tz = timezone(timedelta(hours=4))
        if config['bot']['sleep_start'] <= datetime.now(gulf_tz).hour < config['bot']['sleep_end']:
            return

        feeds = [f['url'] for f in config['sources']['rss_feeds']]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                content_hash = str(hash(entry.title))
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone(): continue

                prompt = f"صغ مقالاً طويلاً (X Premium) عن: {entry.title}. وضح القيمة للفرد من أدوات Google والذكاء الاصطناعي. اذكر المصدر: {url}."
                content = self.generate_ai_content(prompt)

                if content:
                    self.client_v2.create_tweet(text=content)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (hash) VALUES (?)", (content_hash,))
                    logger.info("✅ تم نشر تغريدة استهدافية.")
                    return

    def execute(self):
        """تشغيل النظام بالكامل"""
        self.handle_replies() # فحص الردود أولاً
        self.run_publisher() # ثم النشر

if __name__ == "__main__":
    SovereignBot().execute()
