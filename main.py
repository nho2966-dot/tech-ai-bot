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

        # التحقق من وجود المفاتيح الحيوية
        if not all([gemini_key, x_api_key, x_access_token]):
            raise ValueError("❌ نقص في مفاتيح التشفير! تأكد من إعدادات GitHub Secrets")

        # توثيق X (نظام مزدوج V1 + V2)
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
        
        # إدارة الذاكرة لتجنب التكرار
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
        """نظام النشر الذكي بتبديل آلي للأنظمة"""
        try:
            if reply_to:
                self.x_v2.create_tweet(text=content, in_reply_to_tweet_id=reply_to)
            else:
                self.x_v2.create_tweet(text=content)
            return True
        except Exception as e:
            print(f"⚠️ V2 Failed, trying V1... {e}")
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
        print(f"🚀 دورة تشغيل احترافية: {datetime.now()}")
        
        # 1. معالجة الأخبار (بحد أقصى خبرين دسمين لمنع الإزعاج)
        news_items = self.get_news()
        published_count = 0
        
        for item in news_items:
            if published_count >= 2: break
            
            content_hash = hashlib.md5(item.title.encode()).hexdigest()
            if content_hash in self.state['hashes']: continue

            # صياغة محترفة عبر AI
            prompt = f"صغ هذا الخبر التقني بأسلوب احترافي لمشتركي X، ركز على الفائدة المباشرة: {item.title}"
            ai_content = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt).text.strip()
            
            if self.post_with_fallback(ai_content[:280]):
                self.state['hashes'].append(content_hash)
                published_count += 1
                self.save_state()
                time.sleep(60) # فاصل زمني دقيقة بين التغريدات

        # 2. الردود الذكية (تجاهل الذات والردود المكررة)
        try:
            me_info = self.
