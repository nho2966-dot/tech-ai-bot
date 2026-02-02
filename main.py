import tweepy
import os
import hashlib
import time
import feedparser
import json
from google import genai
from datetime import datetime

# مصادر تقنية عالمية موثوقة
SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://9to5mac.com/feed/",
    "https://techcrunch.com/feed/"
]

class TechProfessionalBot:
    def __init__(self):
        # قراءة المفاتيح بناءً على صورة الـ Secrets الخاصة بك
        gemini_key = os.getenv('GEMINI_KEY')
        x_api_key = os.getenv('X_API_KEY')
        x_api_secret = os.getenv('X_API_SECRET')
        x_access_token = os.getenv('X_ACCESS_TOKEN')
        x_access_secret = os.getenv('X_ACCESS_SECRET')
        x_bearer = os.getenv('X_BEARER_TOKEN')

        if not all([gemini_key, x_api_key, x_access_token]):
            raise ValueError("❌ نقص في مفاتيح التشفير! تأكد من إعدادات GitHub Secrets")

        # توثيق X
        self.x_v2 = tweepy.Client(
            bearer_token=x_bearer,
            consumer_key=x_api_key,
            consumer_secret=x_api_secret,
            access_token=x_access_token,
            access_token_secret=x_access_secret
        )
        
        auth_v1 = tweepy.OAuth1UserHandler(x_api_key, x_api_secret, x_access_token, x_access_secret)
        self.x_v1 = tweepy.API(auth_v1)
        
        # محرك Gemini 2.0
        self.ai = genai.Client(api_key=gemini_key)
        
        self.state_file = 'state.json'
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"hashes": [], "replied_ids": [], "blacklist": []}

    def save_state(self):
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=4)

    def get_news(self):
        news = []
        titles_seen = set()
        for url in SOURCES:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.title.strip()
                if title.lower() not in titles_seen:
                    news.append(entry)
                    titles_seen.add(title.lower())
        return news

    def post_with_fallback(self, content, reply_to=None):
        try:
            if reply_to:
                self.x_v2.create_tweet(text=content, in_reply_to_tweet_id=reply_to)
            else:
                self.x_v2.create_tweet(text=content)
            return True
        except Exception as e:
            print(f"⚠️ V2 Failed: {e}")
            try:
                if reply_to:
                    self.x_v1.update_status(status=content, in_reply_to_status_id=reply_to, auto_populate_reply_metadata=True)
                else:
                    self.x_v1.update_status(status=content)
                return True
            except Exception as e2:
                print(f"❌ Critical Failure: {e2}")
                return False

    def run_cycle(self):
        print(f"🚀 بدء التشغيل: {datetime.now()}")
        
        # 1. نشر الأخبار
        news_items = self.get_news()
        published_count = 0
        for item in news_items:
            if published_count >= 2: break
            content_hash = hashlib.md5(item.title.encode()).hexdigest()
            if content_hash in self.state['hashes']: continue

            prompt = f"صغ هذا الخبر بأسلوب احترافي لمتابعي التقنية: {item.title}"
            ai_content = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt).text.strip()
            
            if self.post_with_fallback(ai_content[:280]):
                self.state['hashes'].append(content_hash)
                published_count += 1
                self.save_state()
                time.sleep(60)

        # 2. الردود الذكية (تم تصحيح السطر المقطوع هنا)
        try:
            me_info = self.x_v2.get_me()
            me_id = me_info.data.id
            mentions = self.x_v2.get_users_mentions(id=me_id).data or []
            
            for tweet in mentions:
                t_id = str(tweet.id)
                if t_id in self.state['replied_ids'] or tweet.author_id == me_id:
                    continue
                
                reply_prompt = f"رد باختصار تقني مفيد على: {tweet.text}"
                reply_msg = self.ai.models.generate_content(model="gemini-2.0-flash", contents=reply_prompt).text.strip()
                
                if self.post_with_fallback(reply_msg[:280], reply_to=tweet.id):
                    self.state['replied_ids'].append(t_id)
                    self.save_state()
                    time.sleep(30)
        except Exception as e:
            print(f"ℹ️ {e}")

if __name__ == "__main__":
    bot = TechProfessionalBot()
    bot.run_cycle()
