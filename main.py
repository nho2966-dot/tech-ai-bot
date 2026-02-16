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

# إعداد اللوج
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("SovereignBot")

def load_config():
    # البحث عن الملف في المجلد الحالي أو المجلد الأب لضمان النجاح في GitHub Actions
    possible_paths = [
        os.path.join(os.getcwd(), "config.yaml"),
        "config.yaml",
        "/home/runner/work/tech-ai-bot/tech-ai-bot/config.yaml"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    
    # إعدادات طوارئ إذا فشل النظام تماماً في إيجاد الملف
    return {
        'bot': {'database_path': 'data/bot.db', 'sleep_start': 0, 'sleep_end': 5},
        'sources': {'rss_feeds': [{'url': 'https://about.google/products/'}]},
        'prompts': {'system_core': 'Artificial Intelligence and its latest tools'}
    }

config = load_config()

class SovereignBot:
    def __init__(self):
        self.db_path = config['bot']['database_path']
        self._init_db()
        self.gemini_key = os.getenv("GEMINI_KEY")
        # المصطلح المعتمد
        self.sys_instruction = "Focus on Artificial Intelligence and its latest tools for individuals, with a Gulf dialect. Be professional and accurate."
        
        # إعداد Twitter API v2
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        try:
            self.bot_id = self.client.get_me().data.id
        except:
            self.bot_id = None

    def _init_db(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir): os.makedirs(db_dir)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def generate_content(self, prompt_text):
        try:
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_text,
                config={'system_instruction': self.sys_instruction}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Gemini Error: {e}")
            return None

    def handle_replies(self):
        """الرد الذكي على الإشارات"""
        if not self.bot_id: return
        try:
            mentions = self.client.get_users_mentions(self.bot_id)
            if not mentions.data: return
            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT tweet_id FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone(): continue
                
                reply_text = self.generate_content(f"رد بذكاء ولهجة خليجية على: {tweet.text}. ركز على فوائد AI وأدوات جوجل.")
                if reply_text:
                    self.client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO replies (tweet_id) VALUES (?)", (str(tweet.id),))
                    time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Reply Error: {e}")

    def run_publisher(self):
        """النشر الاستهدافي الطويل (X Premium)"""
        # توقيت الخليج
        gulf_tz = timezone(timedelta(hours=4))
        hour = datetime.now(gulf_tz).hour
        if config['bot']['sleep_start'] <= hour < config['bot']['sleep_end']: return

        feeds = [f['url'] for f in config['sources']['rss_feeds']]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                content_hash = str(hash(entry.title))
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone(): continue

                # صياغة المنشور الطويل
                prompt = f"اكتب منشوراً طويلاً (Premium) عن أداة أو خبر: {entry.title}. وضح الفائدة للأفراد بلهجة خليجية. المصدر: Google Products."
                content = self.generate_content(prompt)
                
                if content:
                    self.client.create_tweet(text=content)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (hash) VALUES (?)", (content_hash,))
                    return

if __name__ == "__main__":
    bot = SovereignBot()
    bot.handle_replies()
    bot.run_publisher()
