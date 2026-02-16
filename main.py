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

# إعداد اللوج السيادي
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("SovereignBot")

def clean_text(text):
    """تنظيف النصوص لضمان أعلى جودة في معالجة الذكاء الاصطناعي"""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()

class SovereignBot:
    def __init__(self):
        self.db_path = "sovereign_memory.db"
        self._init_db()
        
        # تهيئة عملاء X (الإصدارين 1.1 و 2.0)
        try:
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
            logger.info("✅ تم تهيئة عملاء X بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل تهيئة عملاء X: {e}")
            raise e

        # تهيئة عميل الذكاء الاصطناعي لمرة واحدة
        try:
            self.ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            logger.info("✅ تم تهيئة عميل AI بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل تهيئة AI Client: {e}")
            raise e

        self.user_id = None

    def _init_db(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول إذا لم تكن موجودة"""
        try:
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
            logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            raise e

    def download_image(self, url):
        """تحميل الصورة باسم فريد (UUID) لضمان عدم تداخل العمليات"""
        if not url:
            return None
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                filename = f"temp_img_{uuid.uuid4().hex}.jpg"
                with open(filename, "wb") as f:
                    f.write(response.content)
                return filename
        except Exception as e:
            logger.warning(f"⚠️ فشل تحميل الصورة من الرابط: {e}")
        return None

    def generate_ai_content(self, prompt, is_reply=False):
        sys_msg = (
            "أنت خبير تقني خليجي. ركز على Artificial Intelligence and its latest tools للأفراد. "
            "اللهجة: خليجية بيضاء. استبدل 'الثورة الصناعية' بـ 'Artificial Intelligence and its latest tools'."
        )
        if is_reply: 
            sys_msg += " (رد ذكي وقصير جداً)."
        
        try:
            response = self.ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'system_instruction': sys_msg}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ خطأ AI: {e}")
            return None

    def publish_news(self):
        """جلب الأخبار التقنية وصياغتها ونشرها"""
        feed_urls = [
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
            "https://hnrss.org/newest?q=AI+tools"
        ]
        max_tweets = 3
        posted_count = 0

        for url in feed_urls:
            try:
                feed = feedparser.parse(url)
            except Exception as e:
                logger.warning(f"⚠️ فشل قراءة الـ RSS: {e}")
                continue

            for entry in feed.entries:
                if posted_count >= max_tweets:
                    break

                content_hash = str(hash(entry.title + entry.link))
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT content_hash FROM history WHERE content_hash = ?", (content_hash,)).fetchone():
                        continue

                # استخراج الصورة
                img_url = None
                if 'media_content' in entry:
                    img_url = entry.media_content[0].get('url')
                elif 'media_thumbnail' in entry:
                    img_url = entry.media_thumbnail[0].get('url')
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            img_url = link.href

                prompt = f"حول هذا الخبر لنصيحة خليجية مفيدة: {clean_text(entry.title)}"
                content = self.generate_ai_content(prompt)

                if not content:
                    continue

                media_ids = []
                img_path = self.download_image(img_url) if img_url else None
                if img_path:
                    try:
                        media = self.api_v1.media_upload(filename=img_path)
                        media_ids = [media.media_id]
                        os.remove(img_path)
                    except Exception as e:
                        logger.warning(f"⚠️ فشل رفع الوسائط: {e}")

                try:
                    time.sleep(random.randint(45, 90))
                    self.client_v2.create_tweet(text=content, media_ids=media_ids if media_ids else None)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("INSERT INTO history (content_hash) VALUES (?)", (content_hash,))
                    posted_count += 1
                    logger.info(f"✅ تم نشر التغريدة {posted_count}")
                except Exception as e:
                    logger.error(f"❌ فشل النشر على X: {e}")

    def reply_mentions(self):
        """الرد على المنشنز الذكية"""
        try:
            if not self.user_id:
                self.user_id = self.client_v2.get_me().data.id

            mentions = self.client_v2.get_users_mentions(self.user_id, max_results=10).data
            if not mentions:
                return

            for mention in mentions:
                with sqlite3.connect(self.db_path) as conn:
                    if conn.execute("SELECT mention_id FROM processed_mentions WHERE mention_id = ?", (mention.id,)).fetchone():
                        continue

                prompt = f"رد على هذه التغريدة بذكاء وبلهجة خليجية: {clean_text(mention.text)}"
                reply_text = self.generate_ai_content(prompt, is_reply=True)
                if reply_text:
                    try:
                        self.client_v2.create_tweet(
                            text=f"@{mention.author.username} {reply_text}",
                            in_reply_to_tweet_id=mention.id
                        )
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute("INSERT INTO processed_mentions (mention_id) VALUES (?)", (mention.id,))
                        logger.info(f"✅ تم الرد على المنشن: {mention.id}")
                    except Exception as e:
                        logger.error(f"❌ فشل الرد على المنشن: {e}")

        except Exception as e:
            logger.error(f"❌ خطأ أثناء معالجة المنشنز: {e}")

def main():
    try:
        bot = SovereignBot()
        bot.publish_news()
        bot.reply_mentions()
    except Exception as e:
        logger.error(f"❌ البوت فشل في التشغيل: {e}")

if __name__ == "__main__":
    main()
