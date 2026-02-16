import os
import sqlite3
import feedparser
import tweepy
import time
import random
from datetime import datetime
from google import genai

class SovereignBot:
    def __init__(self):
        # إعدادات الاتصال
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True 
        )
        self.db = sqlite3.connect("data/bot_sovereign.db")
        self.sys_instruction = "Focus on AI tools for individuals. Gulf dialect. Source: Google Products. No hallucinations."

    def handle_mentions(self):
        """إدارة الردود ببطء وتكتيك"""
        try:
            mentions = self.x_client.get_users_mentions(self.x_client.get_me().data.id)
            if not mentions.data: return
            
            for tweet in mentions.data:
                if self._is_processed(f"reply_{tweet.id}"): continue
                
                reply_text = self._generate_ai(f"رد بلهجة خليجية: {tweet.text}")
                if reply_text:
                    try:
                        self.x_client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                        self._mark_processed(f"reply_{tweet.id}")
                        print(f"✅ تم الرد على {tweet.id}")
                        # ⏳ فاصل زمني كبير بين كل رد ورد (مثلاً 30 ثانية) لتجنب الـ 429
                        time.sleep(30) 
                    except tweepy.TooManyRequests:
                        print("⚠️ زحمة طلبات في الردود.. بنهدي اللعب.")
                        break 
        except Exception as e:
            print(f"❌ تنبيه في الردود: {e}")

    def run_hierarchy_publisher(self):
        """النشر بتوقيت منفصل عن الردود"""
        # ننتظر 60 ثانية قبل البدء في النشر لو كان فيه ردود توها مخلصة
        time.sleep(60)
        
        sources = [
            "https://blog.google/products/gemini/rss/",
            "https://techcrunch.com/category/artificial-intelligence/feed/"
        ]
        
        for url in sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                h = str(hash(entry.title))
                if self._is_published(h): continue

                content = self._generate_ai(f"اكتب منشور Premium طويل عن: {entry.title}")
                if content:
                    try:
                        # 🛡️ قبل النشر، نتأكد إننا ما قاعدين نغرد ورا بعض
                        self.x_client.create_tweet(text=content)
                        self._mark_published(h)
                        print(f"✅ تم نشر الخبر من {url}")
                        return # تغريدة واحدة في كل دورة تشغيل تكفي
                    except tweepy.TooManyRequests:
                        print("🛑 تويتر عطانا 429 في النشر.. بننتظر للدورة الجاية.")
                        return

    def _generate_ai(self, prompt):
        try:
            res = self.gemini.models.generate_content(
                model="gemini-2.0-flash", contents=prompt,
                config={'system_instruction': self.sys_instruction}
            )
            return res.text.strip()
        except: return None

    def _is_processed(self, h):
        return self.db.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone() is not None

    def _mark_processed(self, h):
        self.db.execute("INSERT INTO history (hash) VALUES (?)", (h,))
        self.db.commit()

    # نفس الوظائف السابقة للتحقق من النشر...
    def _is_published(self, h): return self._is_processed(h)
    def _mark_published(self, h): self._mark_processed(h)

if __name__ == "__main__":
    bot = SovereignBot()
    # التسلسل الزمني المدروس:
    # 1. خلص الردود أول (بفواصل 30 ثانية)
    bot.handle_mentions()
    
    # 2. ارتاح دقيقة
    time.sleep(60)
    
    # 3. انشر الخبر الهرمي (تغريدة واحدة دسمة)
    bot.run_hierarchy_publisher()
