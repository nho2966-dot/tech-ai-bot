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
        # الربط المزدوج مع X (الأساسي والاحتياطي)
        self.x_v2 = tweepy.Client(
            bearer_token=os.getenv('X_BEARER_TOKEN'),
            consumer_key=os.getenv('X_API_KEY'),
            consumer_secret=os.getenv('X_API_SECRET'),
            access_token=os.getenv('X_ACCESS_TOKEN'),
            access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
        )
        # نظام V1.1 للتحقق ورفع الصور إن وجد
        auth_v1 = tweepy.OAuth1UserHandler(
            os.getenv('X_API_KEY'), os.getenv('X_API_SECRET'),
            os.getenv('X_ACCESS_TOKEN'), os.getenv('X_ACCESS_TOKEN_SECRET')
        )
        self.x_v1 = tweepy.API(auth_v1)
        
        # محرك الذكاء الاصطناعي (Gemini 2.0 Flash)
        self.ai = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        
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
        """جلب الأخبار مع نظام فلترة للمصداقية"""
        news = []
        titles_seen = set()
        for url in SOURCES:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # أول 5 أخبار من كل مصدر
                title = entry.title.strip()
                if title.lower() not in titles_seen:
                    news.append(entry)
                    titles_seen.add(title.lower())
        return news

    def post_with_fallback(self, content, reply_to=None):
        """محاولة النشر بذكاء عبر النظام المتاح"""
        try:
            if reply_to:
                self.x_v2.create_tweet(text=content, in_reply_to_tweet_id=reply_to)
            else:
                self.x_v2.create_tweet(text=content)
            return True
        except Exception as e:
            print(f"⚠️ V2 failed, trying V1... Error: {e}")
            try:
                if reply_to:
                    self.x_v1.update_status(status=content, in_reply_to_status_id=reply_to, auto_populate_reply_metadata=True)
                else:
                    self.x_v1.update_status(status=content)
                return True
            except Exception as e2:
                print(f"❌ Both systems failed: {e2}")
                return False

    def run_cycle(self):
        print(f"🚀 بدء دورة العمل: {datetime.now()}")
        
        # 1. معالجة الأخبار (نشر محدود لتجنب الإزعاج)
        news_items = self.get_news()
        published_count = 0
        
        for item in news_items:
            if published_count >= 2: break # حد أقصى خبرين دسمين في كل دورة
            
            content_hash = hashlib.md5(item.title.encode()).hexdigest()
            if content_hash in self.state['hashes']: continue

            # صياغة محترفة للخبر أو تفنيد الإشاعة
            prompt = f"حلل وصغ هذا الخبر لمتابعين مهتمين بالتقنية في X. إذا كان إشاعة فندها، وإذا كان سبقاً صغه بأسلوب عاجل. الخبر: {item.title}"
            ai_content = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt).text.strip()
            
            # منع التغريدات الطويلة جداً التي قد تزعج البعض
            final_text = ai_content[:500] 

            if self.post_with_fallback(final_text):
                self.state['hashes'].append(content_hash)
                published_count += 1
                self.save_state()
                time.sleep(60) # راحة دقيقة بين الأخبار

        # 2. التفاعل الذكي (الردود)
        try:
            me = self.x_v2.get_me().data.id
            mentions = self.x_v2.get_users_mentions(id=me).data or []
            
            for tweet in mentions:
                t_id = str(tweet.id)
                if t_id in self.state['replied_ids'] or str(tweet.author_id) == str(me): continue
                
                # الرد عبر AI
                reply_prompt = f"رد باختصار وذكاء تقني (لا يتجاوز 200 حرف) على هذا الاستفسار: {tweet.text}"
                reply_msg = self.ai.models.generate_content(model="gemini-2.0-flash", contents=reply_prompt).text.strip()
                
                if self.post_with_fallback(reply_msg, reply_to=tweet.id):
                    self.state['replied_ids'].append(t_id)
                    self.save_state()
                    time.sleep(30) # راحة بين الردود
        except: pass

if __name__ == "__main__":
    bot = TechProfessionalBot()
    bot.run_cycle()
