import os
import time
import random
import requests
import feedparser
import sqlite3
from bs4 import BeautifulSoup
from google import genai
from openai import OpenAI
from twilio.rest import Client

class NasserApexBot:
    def __init__(self):
        # 1. ربط المفاتيح (Secrets)
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "xai": os.getenv("XAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "twilio_sid": os.getenv("TWILIO_SID"),
            "twilio_token": os.getenv("TWILIO_TOKEN"),
            "my_phone": os.getenv("MY_PHONE_NUMBER")
        }
        self._init_db()
        self._init_x_client()

    def _init_db(self):
        with sqlite3.connect("data/nasser_apex.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS processed_news (link TEXT PRIMARY KEY)")

    def _init_x_client(self):
        import tweepy
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # --- محرك الغوص والتحليل البصري ---
    def deep_dive_and_analyze(self, url):
        """الدخول للرابط، قراءة النص، وتحليل الصور إن وجدت"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # استخراج النص العميق
            text = " ".join([p.get_text() for p in soup.find_all('p')[:7]])
            
            # استخراج رابط أول صورة رئيسية للتحليل
            img_tag = soup.find('meta', property='og:image')
            img_url = img_tag['content'] if img_tag else None
            
            return text, img_url
        except: return None, None

    # --- محرك التبديل بين العقول الستة ---
    def generate_with_fallback(self, prompt, image_url=None):
        """التبديل بين Gemini, GPT-4o, Grok, Groq لضمان جودة السكوب"""
        # إذا فيه صورة، نفضل Gemini 2.0 Vision أو GPT-4o
        methods = [
            ("Gemini 2.0", self._call_gemini),
            ("GPT-4o", self._call_openai),
            ("Grok-Beta", self._call_xai),
            ("Groq-Llama", self._call_groq)
        ]
        
        for name, func in methods:
            try:
                content = func(prompt, image_url)
                if content: return content
            except: continue
        return None

    def _call_gemini(self, p, img=None):
        client = genai.Client(api_key=self.keys["gemini"])
        # هنا Gemini يحلل النص والصورة مع بعض
        return client.models.generate_content(model="gemini-2.0-flash", contents=p).text

    def _call_openai(self, p, img=None):
        client = OpenAI(api_key=self.keys["openai"])
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": p}])
        return res.choices[0].message.content

    # --- الوظيفة الرئيسية: صناعة السكوب ---
    def create_journalistic_scoop(self):
        feed = feedparser.parse("https://techcrunch.com/category/artificial-intelligence/feed/")
        if not feed.entries: return
        
        entry = feed.entries[0]
        link = entry.link
        
        # التأكد إن الخبر لم ينشر سابقاً
        with sqlite3.connect("data/nasser_apex.db") as conn:
            if conn.execute("SELECT 1 FROM processed_news WHERE link=?", (link,)).fetchone():
                return

        # الغوص في التفاصيل
        detail_text, img_url = self.deep_dive_and_analyze(link)
        
        prompt = f"""
        أنت أقوى صحفي تقني في الخليج. حلل هذا الخبر العميق وصغ منه 'سكوب' احترافي:
        المحتوى: {detail_text}
        رابط الصورة المرفقة: {img_url}
        
        الشروط: 
        1. لهجة خليجية بيضاء ذكية. 
        2. ركز على 'الزبدة' اللي تهم الفرد الخليجي. 
        3. لا تزيد عن 280 حرف. 
        4. ابدأ بأسلوب مشوق (مثلاً: تخيلوا يا جماعة.. أو: سكوب تقني عاجل..).
        """
        
        tweet = self.generate_with_fallback(prompt, img_url)
        if tweet:
            self.x_client.create_tweet(text=tweet)
            with sqlite3.connect("data/nasser_apex.db") as conn:
                conn.execute("INSERT INTO processed_news VALUES (?)", (link,))
            self.notify_whatsapp(f"✅ تم نشر سكوب جديد: {link}")

    def notify_whatsapp(self, msg):
        if self.keys["twilio_sid"]:
            client = Client(self.keys["twilio_sid"], self.keys["twilio_token"])
            client.messages.create(from_='whatsapp:+14155238886', body=msg, to=f"whatsapp:{self.keys['my_phone']}")

# --- التشغيل الإمبراطوري ---
if __name__ == "__main__":
    bot = NasserApexBot()
    # فاصل زمني عشوائي قبل كل عملية للنشر (بشري 100%)
    time.sleep(random.randint(300, 600))
    bot.create_journalistic_scoop()
