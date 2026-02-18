import os
import sys
import time
import yaml
import random
import sqlite3
import pathlib
import requests
import feedparser
import tweepy
from bs4 import BeautifulSoup
from google import genai
from openai import OpenAI

class NasserApexBot:
    def __init__(self):
        self.config = self._find_and_load_config()
        self._init_db()
        self._init_clients()
        print(f"✅ تم تشغيل {self.config['logging']['name']} بنجاح.")

    # --- 1. البحث عن ملف الإعدادات في أي مكان ---
    def _find_and_load_config(self):
        root_dir = pathlib.Path(__file__).parent.parent if "__file__" in locals() else pathlib.Path.cwd()
        config_path = next(root_dir.glob("**/config.yaml"), None)
        if not config_path:
            raise FileNotFoundError("❌ يا ناصر، ملف config.yaml مفقود!")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_db(self):
        db_path = self.config['bot']['database_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied (id TEXT PRIMARY KEY)")

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.has_wa = False
        if self.config['bot'].get('wa_notify'):
            try:
                from twilio.rest import Client
                self.wa_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
                self.has_wa = True
            except: print("⚠️ مكتبة الواتساب غير مثبتة.")

    # --- 2. محرك العقول الستة البديلة (The Council of Six) ---
    def generate_content(self, mode_key, content_input=""):
        system_core = self.config['prompts']['system_core']
        mode_prompt = self.config['prompts']['modes'][mode_key].format(content=content_input)
        full_prompt = f"{system_core}\n\nالمهمة الحالية: {mode_prompt}"

        for model_cfg in self.config['models']['priority']:
            try:
                api_key = os.getenv(model_cfg['env_key'])
                if not api_key: continue
                
                print(f"🤖 محاولة التوليد عبر: {model_cfg['name']}...")
                if model_cfg['type'] == "google":
                    c = genai.Client(api_key=api_key)
                    res = c.models.generate_content(model=model_cfg['model'], contents=full_prompt)
                    return res.text
                elif model_cfg['type'] in ["openai", "xai", "groq", "openrouter"]:
                    urls = {"xai": "https://api.x.ai/v1", "groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
                    c = OpenAI(api_key=api_key, base_url=urls.get(model_cfg['type']))
                    res = c.chat.completions.create(model=model_cfg['model'], messages=[{"role": "user", "content": full_prompt}])
                    return res.choices[0].message.content
            except: continue
        return None

    # --- 3. صمام أمان عدم الاقتطاع والفلاتر ---
    def finalize_text(self, text):
        """ضمان عدم اقتطاع النص والحفاظ على المعنى"""
        if not text or any(word in text for word in ["أعتذر", "لا يوجد", "المرسل", "تخطي"]):
            return None
        
        # تنظيف من أي رموز أو لغات غريبة
        clean_text = text.strip().split('\n')[0] 
        
        if len(clean_text) <= 280:
            return clean_text
        
        # القص الذكي عند آخر نقطة
        truncated = clean_text[:277]
        last_dot = truncated.rfind('.')
        if last_dot > 180:
            return truncated[:last_dot + 1]
        
        # إذا لم توجد نقطة، القص عند آخر مسافة
        return truncated[:truncated.rfind(' ')] + "..."

    # --- 4. نظام الردود الذكية (Smart Replies) ---
    def handle_mentions(self):
        print("🔍 فحص المنشن...")
        try:
            me = self.x_client.get_me()
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions or not mentions.data: return

            for tweet in mentions.data:
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM replied WHERE id=?", (str(tweet.id),)).fetchone(): continue
                
                reply = self.finalize_text(self.generate_content("REPLY", tweet.text))
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO replied VALUES (?)", (str(tweet.id),))
                    time.sleep(random.randint(30, 60))
        except Exception as e: print(f"⚠️ خطأ ردود: {e}")

    # --- 5. الغوص العميق ونشر السكوبات ---
    def run_scoop_mission(self):
        print("📰 جاري الغوص في الأخبار...")
        for feed_cfg in self.config['sources']['rss_feeds']:
            feed = feedparser.parse(feed_cfg['url'])
            if not feed.entries: continue
            
            entry = feed.entries[0]
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM processed WHERE id=?", (entry.link,)).fetchone(): continue

            try:
                # الغوص العميق لاستخراج النص
                res = requests.get(entry.link, headers={"User-Agent": self.config['bot']['user_agent']}, timeout=10)
                soup = BeautifulSoup(res.content, "html.parser")
                paragraphs = [p.get_text() for p in soup.find_all('p') if len(p.get_text()) > 60]
                article_body = " ".join(paragraphs[:5])

                if len(article_body) < 300: continue # حماية من المقالات الفارغة

                tweet = self.finalize_text(self.generate_content("POST_DEEP", article_body))
                if tweet:
                    self.x_client.create_tweet(text=tweet)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO processed VALUES (?, CURRENT_TIMESTAMP)", (entry.link,))
                    self.notify_wa(f"✅ تم نشر سكوب: {entry.title}")
                    break # نشر خبر واحد لكل دورة
            except: continue

    def notify_wa(self, msg):
        if self.has_wa:
            try:
                self.wa_client.messages.create(from_='whatsapp:+14155238886', body=f"🤖 *أيبكس:* {msg}", to=f"whatsapp:{os.getenv('MY_PHONE_NUMBER')}")
            except: pass

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.handle_mentions() # ابدأ بالردود
    time.sleep(random.randint(300, 600)) # فاصل بشري (5-10 دقائق)
    bot.run_scoop_mission() # ثم النشر العميق
