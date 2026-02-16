import os
import time
import random
import logging
import feedparser
import tweepy
import sqlite3
from datetime import datetime
from google import genai

# إعداد اللوج السيادي
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("SovereignBot")

class SovereignBot:
    def __init__(self):
        self.db_path = "sovereign_memory.db"
        self._init_db()
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        # معرف الحساب ثابت لتقليل استدعاءات get_me (توفيراً للـ API)
        self.user_id = None 

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (content_hash TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE IF NOT EXISTS processed_mentions (mention_id TEXT PRIMARY KEY)")

    def apply_delay(self, min_sec=30, max_sec=60):
        """فاصل زمني إجباري لمحاكاة النشاط البشري وتجنب الـ Rate Limit"""
        wait = random.randint(min_sec, max_sec)
        logger.info(f"⏳ فاصل زمني سيادي: الانتظار {wait} ثانية...")
        time.sleep(wait)

    def generate_ai_content(self, prompt, is_reply=False):
        sys_msg = (
            "أنت خبير تقني خليجي. ركز حصراً على ممارسات Artificial Intelligence and its latest tools "
            "التي تخدم الأفراد وتطورهم الشخصي. اللهجة: خليجية بيضاء راقية. "
            "تجنب ذكر المؤسسات. استبدل 'الثورة الصناعية' دائماً بـ 'Artificial Intelligence and its latest tools'."
        )
        if is_reply: sys_msg += " (أنت ترد على منشن، اجعل الرد شخصي وقصير جداً)."
        
        try:
            ai_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'system_instruction': sys_msg}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ خطأ AI: {e}")
            return None

    def process_mentions(self):
        """معالجة الردود الذكية بذكاء وفاصل زمني"""
        try:
            if not self.user_id:
                me = self.client.get_me()
                self.user_id = me.data.id
            
            mentions = self.client.get_users_mentions(self.user_id)
            if not mentions.data: return

            with sqlite3.connect(self.db_path) as conn:
                for tweet in mentions.data:
                    res = conn.execute("SELECT mention_id FROM processed_mentions WHERE mention_id = ?", (tweet.id,)).fetchone()
                    if res: continue

                    reply_text = self.generate_ai_content(tweet.text, is_reply=True)
                    if reply_text:
                        self.apply_delay(20, 40) # تأخير قبل الرد
                        self.client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                        conn.execute("INSERT INTO processed_mentions (mention_id) VALUES (?)", (tweet.id,))
                        logger.info(f"✅ تم الرد على {tweet.id}")
        except Exception as e:
            logger.warning(f"⚠️ تنبيه المنشنز (قد يكون اشتراكك لا يدعمها أو Rate Limit): {e}")

    def publish_news(self):
        """نشر محتوى جديد مع فلترة صارمة للأفراد"""
        feed = feedparser.parse("https://hnrss.org/newest?q=AI+tools+individual")
        if not feed.entries: return

        for entry in feed.entries[:2]:
            self.apply_delay(40, 80) # تأخير إجباري قبل النشر
            content = self.generate_ai_content(f"لخص للأفراد: {entry.title}")
            
            if content:
                try:
                    self.client.create_tweet(text=content)
                    logger.info("✅ تم النشر بنجاح!")
                    break # نكتفي بواحدة لضمان السيادة
                except Exception as e:
                    logger.error(f"❌ خطأ نشر: {e}")

def main():
    bot = SovereignBot()
    # تنفيذ المهام ببطء وتوازن
    bot.process_mentions()
    bot.publish_news()

if __name__ == "__main__":
    main()
