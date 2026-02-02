import tweepy
import os
import hashlib
import time
import feedparser
import json
from google import genai
from datetime import datetime

# --- الإعدادات والمصادر ---
SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://9to5mac.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/category/security/rss"
]

class TechPressEngine:
    def __init__(self):
        # توثيق X (V1 + V2)
        self.x_v2 = tweepy.Client(
            bearer_token=os.getenv('X_BEARER_TOKEN'),
            consumer_key=os.getenv('X_API_KEY'),
            consumer_secret=os.getenv('X_API_SECRET'),
            access_token=os.getenv('X_ACCESS_TOKEN'),
            access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
        )
        auth_v1 = tweepy.OAuth1UserHandler(
            os.getenv('X_API_KEY'), os.getenv('X_API_SECRET'),
            os.getenv('X_ACCESS_TOKEN'), os.getenv('X_ACCESS_TOKEN_SECRET')
        )
        self.x_v1 = tweepy.API(auth_v1)
        
        # توثيق Gemini
        self.ai = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        
        # الذاكرة المحلية (State)
        self.state_file = 'state.json'
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f: return json.load(f)
        return {"hashes": [], "replied_ids": [], "blacklist": []}

    def save_state(self):
        with open(self.state_file, 'w') as f: json.dump(self.state, f)

    def get_verified_news(self):
        """رصد الأخبار والتحقق المتقاطع"""
        found_titles = {}
        for url in SOURCES:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                t = entry.title.strip().lower()
                found_titles[t] = found_titles.get(t, [])
                found_titles[t].append(entry)
        
        # اختيار الأخبار التي ظهرت في أكثر من مصدر (تأكيد) أو عاجل
        return [entries[0] for t, entries in found_titles.items() if len(entries) > 1 or "breaking" in t]

    def smart_publish(self, content):
        """نظام النشر المزدوج الاحترافي"""
        h = hashlib.md5(content.encode()).hexdigest()
        if h in self.state['hashes']: return False

        try:
            self.x_v2.create_tweet(text=content)
            self.state['hashes'].append(h)
            self.save_state()
            return True
        except Exception as e:
            try:
                self.x_v1.update_status(status=content)
                self.state['hashes'].append(h)
                self.save_state()
                return True
            except:
                print(f"❌ فشل النشر: {e}")
                return False

    def handle_mentions(self):
        """الردود الذكية وفلترة المشاعر والقائمة السوداء"""
        try:
            me = self.x_v2.get_me().data.id
            mentions = self.x_v2.get_users_mentions(id=me).data or []
            
            for tweet in mentions:
                t_id = str(tweet.id)
                u_id = str(tweet.author_id)
                
                if u_id == str(me) or t_id in self.state['replied_ids'] or u_id in self.state['blacklist']:
                    continue

                # تحليل المشاعر قبل الرد (نظام الحماية)
                analysis_prompt = f"حلل نبرة هذا النص: '{tweet.text}'. إذا كان سباً أو إهانة رد بكلمة 'BAD'، غير ذلك رد بـ 'GOOD'."
                sentiment = self.ai.models.generate_content(model="gemini-2.0-flash", contents=analysis_prompt).text
                
                if "BAD" in sentiment:
                    self.state['blacklist'].append(u_id)
                    self.save_state()
                    continue

                # توليد الرد
                reply_prompt = f"رد باختصار كخبير تقني على: {tweet.text}"
                reply_text = self.ai.models.generate_content(model="gemini-2.0-flash", contents=reply_prompt).text
                
                if self.smart_publish_reply(reply_text.strip(), tweet.id):
                    self.state['replied_ids'].append(t_id)
                    self.save_state()
        except Exception as e:
            print(f"⚠️ خطأ في المنشنز: {e}")

    def smart_publish_reply(self, text, reply_id):
        try:
            self.x_v2.create_tweet(text=text, in_reply_to_tweet_id=reply_id)
            return True
        except: return False

    def run(self):
        print(f"🛡️ المحرك يعمل... {datetime.now()}")
        # 1. نشر الأخبار
        news = self.get_verified_news()
        for item in news[:3]: # نشر أفضل 3 أخبار فقط في الدورة
            prompt = f"صغ هذا الخبر كسبق صحفي أو تفنيد إشاعة لمشتركي X: {item.title}\n{item.summary}"
            content = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
            if self.smart_publish(content.strip()):
                print(f"✅ تم نشر: {item.title[:30]}...")
                time.sleep(30) # فجوة زمنية بسيطة

        # 2. معالجة التفاعل
        self.handle_mentions()

if __name__ == "__main__":
    bot = TechPressEngine()
    bot.run()
