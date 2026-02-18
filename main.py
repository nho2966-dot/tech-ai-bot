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
        print(f"✅ تم تحميل الإعدادات وبدء تشغيل: {self.config['logging']['name']}")

    # --- 1. رادار البحث عن ملف الإعدادات ---
    def _find_and_load_config(self):
        root_dir = pathlib.Path(__file__).parent.parent if "__file__" in locals() else pathlib.Path.cwd()
        config_path = next(root_dir.glob("**/config.yaml"), None)
        if not config_path:
            raise FileNotFoundError("❌ يا ناصر، ملف config.yaml غير موجود في أي مكان بالمشروع!")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_db(self):
        db_path = self.config['bot']['database_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY, type TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied_mentions (tweet_id TEXT PRIMARY KEY)")

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
            except: print("⚠️ فشل تحميل مكتبة الواتساب")

    # --- 2. محرك العقول الستة البديلة ---
    def generate_content(self, mode_key, content_input=""):
        system_prompt = self.config['prompts']['system_core']
        user_prompt = self.config['prompts']['modes'][mode_key].format(content=content_input)
        full_prompt = f"{system_prompt}\n\nالمهمة: {user_prompt}"

        for model_cfg in self.config['models']['priority']:
            try:
                api_key = os.getenv(model_cfg['env_key'])
                if not api_key: continue
                
                if model_cfg['type'] == "google":
                    client = genai.Client(api_key=api_key)
                    res = client.models.generate_content(model=model_cfg['model'], contents=full_prompt)
                    return res.text
                elif model_cfg['type'] in ["openai", "xai", "groq", "openrouter"]:
                    base_urls = {"xai": "https://api.x.ai/v1", "groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
                    client = OpenAI(api_key=api_key, base_url=base_urls.get(model_cfg['type']))
                    res = client.chat.completions.create(model=model_cfg['model'], messages=[{"role": "user", "content": full_prompt}])
                    return res.choices[0].message.content
            except: continue
        return None

    # --- 3. نظام الردود الذكية (Smart Replies) ---
    def handle_mentions(self):
        print("🔍 فحص المنشن للرد الذكي...")
        try:
            # جلب معرف البوت تلقائياً
            me = self.x_client.get_me()
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            
            if not mentions or not mentions.data:
                print("ℹ️ لا يوجد منشن جديد.")
                return

            for tweet in mentions.data:
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM replied_mentions WHERE tweet_id=?", (str(tweet.id),)).fetchone():
                        continue
                
                print(f"💬 جاري الرد على: {tweet.text[:50]}...")
                reply_text = self.generate_content("REPLY", tweet.text)
                
                if reply_text:
                    self.x_client.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO replied_mentions VALUES (?)", (str(tweet.id),))
                    
                    # فاصل زمني صغير بين الردود (سلوك بشري)
                    time.sleep(random.randint(30, 60))
        except Exception as e:
            print(f"⚠️ خطأ في نظام الردود: {e}")

    # --- 4. نظام النشر والسكوبات العميقة ---
    def run_scoop_mission(self):
        print("📰 جاري البحث عن سكوب عميق...")
        for feed_cfg in self.config['sources']['rss_feeds']:
            feed = feedparser.parse(feed_cfg['url'])
            if not feed.entries: continue
            
            entry = feed.entries[0]
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM processed WHERE id=?", (entry.link,)).fetchone():
                    continue

            # الغوص العميق (Scraping)
            res = requests.get(entry.link, headers={"User-Agent": self.config['bot']['user_agent']})
            soup = BeautifulSoup(res.content, "html.parser")
            article_text = " ".join([p.get_text() for p in soup.find_all('p')[:5]])

            tweet = self.generate_content("POST_DEEP", article_text)
            if tweet:
                self.x_client.create_tweet(text=tweet[:280])
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    conn.execute("INSERT INTO processed VALUES (?, 'news')", (entry.link,))
                self.notify_nasser(f"✅ تم نشر سكوب عميق عن: {entry.title}")
                break

    def notify_nasser(self, msg):
        print(f"📢 {msg}")
        if self.has_wa:
            try:
                self.wa_client.messages.create(
                    from_='whatsapp:+14155238886',
                    body=f"🤖 *أيبكس:* {msg}",
                    to=f"whatsapp:{os.getenv('MY_PHONE_NUMBER')}"
                )
            except: pass

# --- الدورة التشغيلية المنسقة ---
if __name__ == "__main__":
    bot = NasserApexBot()
    
    # 1. أولاً: الرد على الناس (الأولوية للتفاعل)
    bot.handle_mentions()
    
    # 2. فاصل زمني "بشري" (5-10 دقائق) قبل النشر
    delay = random.randint(300, 600)
    print(f"⏳ سكون لمدة {delay//60} دقيقة لضمان السيادة الرقمية...")
    time.sleep(delay)
    
    # 3. ثانياً: نشر السكوب العميق
    bot.run_scoop_mission()
