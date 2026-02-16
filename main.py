import os
import time
import random
import logging
import feedparser
import tweepy
import sqlite3
import re
import requests
import uuid
from datetime import datetime
from google import genai

# -------------------------
# إعداد اللوج السيادي
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("SovereignBot")

# -------------------------
# دوال مساعدة
# -------------------------
def clean_text(text):
    """تنظيف النصوص لإزالة الروابط والوسوم"""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()

def apply_delay(min_sec=40, max_sec=90):
    """تأخير عشوائي لمحاكاة النشاط البشري"""
    wait = random.randint(min_sec, max_sec)
    logger.info(f"⏳ انتظار {wait} ثانية لتقليل خطر الحظر...")
    time.sleep(wait)

# -------------------------
# بوت السيادة
# -------------------------
class SovereignBot:
    def __init__(self):
        # قاعدة البيانات
        self.db_path = "sovereign_memory.db"
        self._init_db()

        # إعداد عملاء X
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

        # عميل الذكاء الاصطناعي
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.user_id = None

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    content_hash TEXT PRIMARY KEY, 
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_mentions (
                    mention_id TEXT PRIMARY KEY, 
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    # -------------------------
    # رفع الصور
    # -------------------------
    def download_image(self, url):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                filename = f"temp_img_{uuid.uuid4().hex}.jpg"
                with open(filename, "wb") as f:
                    f.write(response.content)
                return filename
        except Exception as e:
            logger.warning(f"⚠️ فشل تحميل الصورة: {e}")
        return None

    # -------------------------
    # توليد المحتوى AI
    # -------------------------
    def generate_ai_content(self, prompt, is_reply=False):
        sys_msg = (
            "أنت خبير تقني خليجي. ركز على Artificial Intelligence and its latest tools للأفراد. "
            "اللهجة: خليجية بيضاء. استبدل 'الثورة الصناعية' بـ 'Artificial Intelligence and its latest tools'."
        )
        if is_reply: sys_msg += " (رد ذكي وقصير جداً)."

        try:
            res = self.ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'system_instruction': sys_msg}
            )
            return res.text.strip()
        except Exception as e:
            logger.error(f"❌ خطأ AI: {e}")
            return None

    # -------------------------
    # النشر من RSS
    # -------------------------
    def publish_news(self):
        feed_urls = [
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
            "https://hnrss.org/newest?q=AI+tools"
        ]
        max_tweets = 3
        posted_count = 0

        for url in feed_urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if posted_count >= max_tweets: break

                content_hash = str(hash(entry.title + entry.link))
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT content_hash FROM history WHERE content_hash = ?", (content_hash,)).fetchone():
                        continue

                # استخراج الصورة
                img_url = None
                if 'media_content' in entry: img_url = entry.media_content[0].get('url')
                elif 'media_thumbnail' in entry: img_url = entry.media_thumbnail[0].get('url')
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''): img_url = link.href

                # توليد محتوى AI
                prompt = f"حول هذا الخبر لنصيحة خليجية مفيدة: {clean_text(entry.title)}"
                content = self.generate_ai_content(prompt)
                if not content: continue

                media_ids = []
                img_path = self.download_image(img_url) if img_url else None
                if img_path:
                    try:
                        media = self.api_v1.media_upload(filename=img_path)
                        media_ids = [media.media_id]
                        os.remove(img_path)
                    except Exception as e:
                        logger.warning(f"⚠️ خطأ رفع الصورة: {e}")

                apply_delay(45, 90)
                try:
                    self.client_v2.create_tweet(text=content, media_ids=media_ids if media_ids else None)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (content_hash) VALUES (?)", (content_hash,))
                    logger.info(f"✅ تم نشر التغريدة {posted_count + 1}")
                    posted_count += 1
                except Exception as e:
                    logger.error(f"❌ خطأ نشر التغريدة: {e}")

    # -------------------------
    # الرد على المنشنات
    # -------------------------
    def process_mentions(self):
        try:
            if not self.user_id:
                me = self.client_v2.get_me()
                self.user_id = me.data.id

            mentions = self.client_v2.get_users_mentions(self.user_id, max_results=10)
            if not mentions or not mentions.data:
                logger.info("ℹ️ لا توجد منشنات جديدة")
                return

            with sqlite3.connect(self.db_path) as conn:
                for tweet in mentions.data:
                    if conn.execute("SELECT mention_id FROM processed_mentions WHERE mention_id = ?", (tweet.id,)).fetchone():
                        continue

                    reply_text = self.generate_ai_content(clean_text(tweet.text), is_reply=True)
                    if reply_text:
                        apply_delay(30, 60)
                        try:
                            self.client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                            conn.execute("INSERT INTO processed_mentions (mention_id) VALUES (?)", (tweet.id,))
                            logger.info(f"✅ تم الرد على المنشن {tweet.id}")
                        except Exception as e:
                            logger.error(f"❌ خطأ في الرد على المنشن: {e}")

# -------------------------
# التنفيذ الرئيسي
# -------------------------
def main():
    bot = SovereignBot()
    bot.process_mentions()
    bot.publish_news()

if __name__ == "__main__":
    main()
