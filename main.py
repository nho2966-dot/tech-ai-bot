import os
import yaml
import sqlite3
import logging
import time
import feedparser
import tweepy
from datetime import datetime, timedelta, timezone
from google import genai

# 1. إعداد اللوج بشكل احترافي
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
logger = logging.getLogger("SovereignBot")

def load_config():
    # استخدام المسار المطلق لضمان عدم حدوث FileNotFoundError في GitHub Actions
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.yaml")
    
    if not os.path.exists(config_path):
        logger.error(f"❌ ملف config.yaml غير موجود في: {config_path}")
        # إعدادات طوارئ ذكية (بديلة) لمنع توقف البوت
        return {
            'bot': {'database_path': 'data/bot_history.db', 'sleep_start': 0, 'sleep_end': 6},
            'sources': {'rss_feeds': [{'url': 'https://blog.google/products/gemini/rss/'}]},
            'prompts': {'system_core': 'Focus on AI tools for individuals.'}
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

class SovereignBot:
    def __init__(self):
        # إعداد قاعدة البيانات والتأكد من وجود المجلد
        db_path = config['bot']['database_path']
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir): os.makedirs(db_dir)
        
        self.db_path = db_path
        self._init_db()
        self.gemini_key = os.getenv("GEMINI_KEY")
        
        # التوجيهات الصارمة (System Instruction) لمنع الهلوسة والزهايمر
        self.sys_instruction = (
            "Focus on Artificial Intelligence and its latest tools for individuals, with a Gulf dialect. "
            "Be updated with the latest Google tools. Replace any mention of 'Industrial Revolution' "
            "with 'Artificial Intelligence and its latest tools'. No hallucinations. No symbols. "
            "Avoid Chinese languages. Focus on news for individuals, not companies."
        )
        
        # إعداد Twitter API v2 (يدعم المنشورات الطويلة والردود)
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        try:
            self.bot_id = self.client.get_me().data.id
        except Exception as e:
            logger.error(f"⚠️ فشل جلب ID البوت: {e}")
            self.bot_id = None

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def generate_ai_text(self, prompt):
        try:
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ خطأ في Gemini: {e}")
            return None

    def handle_mentions(self):
        """الردود الذكية على الإشارات (Mentions)"""
        if not self.bot_id: return
        logger.info("📡 فحص المنشن للردود...")
        try:
            mentions = self.client.get_users_mentions(self.bot_id)
            if not mentions.data: return
            
            for tweet in mentions.data:
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT tweet_id FROM replies WHERE tweet_id=?", (str(tweet.id),)).fetchone():
                        continue
                
                logger.info(f"💬 جاري الرد على: {tweet.id}")
                prompt = f"رد بلهجة خليجية بيضاء وبدون هلوسة على هذه التغريدة: {tweet.text}. ركز على فوائد أدوات الذكاء الاصطناعي."
                reply_text = self.generate_ai_text(prompt)
                
                if reply_text:
                    self.client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO replies (tweet_id) VALUES (?)", (str(tweet.id),))
                    time.sleep(2)
        except Exception as e:
            logger.error(f"❌ خطأ في الردود: {e}")

    def publish_long_post(self):
        """النشر الاستهدافي الطويل (X Premium)"""
        gulf_tz = timezone(timedelta(hours=4))
        now_hour = datetime.now(gulf_tz).hour
        
        # تجنب النشر في أوقات النوم المحددة
        if config['bot']['sleep_start'] <= now_hour < config['bot']['sleep_end']:
            logger.info("🌙 توقيت نوم البوت (حسب توقيت الخليج).")
            return

        logger.info("📰 فحص المصادر للنشر الاستهدافي...")
        for feed_info in config['sources']['rss_feeds']:
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:1]:
                content_hash = str(hash(entry.title))
                
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT hash FROM history WHERE hash=?", (content_hash,)).fetchone():
                        continue
                
                prompt = (
                    f"صغ منشوراً طويلاً (Premium) عن هذا الخبر/الأداة: {entry.title}. "
                    f"وضح الفائدة المباشرة للفرد وادمج أحدث أدوات Google. المصدر: {feed_info['url']}. "
                    f"اللهجة خليجية بيضاء، المصطلحات إنجليزية بين قوسين، وبدون مبالغات."
                )
                
                post_content = self.generate_ai_text(prompt)
                if post_content:
                    self.client.create_tweet(text=post_content)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (hash) VALUES (?)", (content_hash,))
                    logger.info("✅ تم نشر المنشور الاستهدافي.")
                    return # نشر منشور واحد في الدورة الواحدة

if __name__ == "__main__":
    bot = SovereignBot()
    bot.handle_mentions()
    bot.publish_long_post()
