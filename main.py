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
import logging
import hashlib
from datetime import datetime, date
from collections import deque
from bs4 import BeautifulSoup
from google import genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# إعدادات التسجيل - إمبراطورية ناصر التقنية
logging.basicConfig(level=logging.INFO, format="🛡️ [أيبكس]: %(message)s")

# --- الثوابت السيادية ---
MAX_TWEET_LENGTH = 280
MAX_DAILY_POSTS = 5
MAX_RETRIES = 3
DELAY_MIN = 40
DELAY_MAX = 90

def _find_and_load_config():
    root_dir = pathlib.Path(__file__).parent.parent if "__file__" in locals() else pathlib.Path.cwd()
    config_path = next(root_dir.glob("**/config.yaml"), None)
    if not config_path:
        # محاولة أخيرة للبحث في المجلد الحالي
        config_path = pathlib.Path("config.yaml")
        
    if not config_path.exists():
        raise FileNotFoundError("❌ ملف config.yaml مفقود!")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class NasserApexBot:
    def __init__(self):
        self.config = _find_and_load_config()
        self._init_db()
        self._init_clients()
        logging.info(f"✅ تم تشغيل البوت بنجاح. الهوية: {self.config['logging']['name']}")

    def _init_db(self):
        db_path = self.config['bot']['database_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied (id TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")

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
            except: logging.warning("⚠️ الواتساب غير مفعل.")

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=15))
    def generate_content(self, mode_key, content_input=""):
        system_core = self.config['prompts']['system_core']
        mode_prompt = self.config['prompts']['modes'][mode_key].format(content=content_input)
        full_prompt = f"{system_core}\n\nالمهمة: {mode_prompt}"

        for model_cfg in self.config['models']['priority']:
            try:
                api_key = os.getenv(model_cfg['env_key'])
                if not api_key: continue
                
                logging.info(f"🤖 محاولة التوليد عبر عقل: {model_cfg['name']}")
                
                if model_cfg['type'] == "google":
                    c = genai.Client(api_key=api_key)
                    res = c.models.generate_content(model=model_cfg['model'], contents=full_prompt)
                    return self.finalize_text(res.text)
                
                elif model_cfg['type'] in ["openai", "xai", "groq", "openrouter"]:
                    urls = {
                        "xai": "https://api.x.ai/v1", 
                        "groq": "https://api.groq.com/openai/v1", 
                        "openrouter": "https://openrouter.ai/api/v1"
                    }
                    c = OpenAI(api_key=api_key, base_url=urls.get(model_cfg['type']))
                    res = c.chat.completions.create(model=model_cfg['model'], messages=[{"role": "user", "content": full_prompt}])
                    return self.finalize_text(res.choices[0].message.content)
            except Exception as e:
                logging.error(f"⚠️ تعثر {model_cfg['name']}: {str(e)[:50]}")
                continue
        return None

    def finalize_text(self, text):
        if not text or len(text.strip()) < 40: return None
        blacklist = ["أعتذر", "لا يوجد", "حسناً", "دعنا", "المرسل", "تخطي", "عفواً"]
        if any(x in text for x in blacklist): return None
        
        clean_text = text.replace("\n\n", "\n").strip()
        if len(clean_text) <= MAX_TWEET_LENGTH: return clean_text
        
        truncated = clean_text[:MAX_TWEET_LENGTH - 5]
        last_stop = max(truncated.rfind('.'), truncated.rfind('؟'), truncated.rfind('!'))
        return truncated[:last_stop + 1] if last_stop > 150 else None

    def handle_mentions(self):
        try:
            me = self.x_client.get_me()
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions or not mentions.data: return
            
            for tweet in mentions.data:
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM replied WHERE id=?", (str(tweet.id),)).fetchone(): continue
                
                reply = self.generate_content("REPLY", tweet.text)
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO replied VALUES (?)", (str(tweet.id),))
                    time.sleep(random.randint(DELAY_MIN, DELAY_MAX))
        except Exception as e: logging.error(f"⚠️ خطأ ردود: {e}")

    def run_scoop_mission(self):
        logging.info("🔍 رصد السكوبات الرباعية...")
        for feed_cfg in self.config['sources']['rss_feeds']:
            feed = feedparser.parse(feed_cfg['url'])
            if not feed.entries: continue
            entry = feed.entries[0]
            
            # تحديد المنشن الخاص بالمصدر لزيادة الريتش
            source_handle = "@verge" if "theverge" in entry.link else "@TechCrunch"
            
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM processed WHERE id=?", (entry.link,)).fetchone(): continue

            try:
                res = requests.get(entry.link, headers={"User-Agent": self.config['bot']['user_agent']}, timeout=10)
                soup = BeautifulSoup(res.content, "html.parser")
                paragraphs = [p.get_text() for p in soup.find_all('p') if len(p.get_text()) > 80]
                article_body = f"Source Handle: {source_handle} | News Content: " + " ".join(paragraphs[:5])

                tweet = self.generate_content("POST_DEEP", article_body)
                if tweet:
                    self.publish(tweet)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO processed VALUES (?, CURRENT_TIMESTAMP)", (entry.link,))
                    self.notify_wa(f"✅ نُشر سكوب جديد: {entry.title}")
                    break 
            except Exception as e:
                logging.error(f"❌ فشل في مهمة السكوب: {e}")

    def publish(self, text):
        try:
            h = hashlib.sha256(text.encode()).hexdigest()
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    logging.warning("⚠️ محتوى مكرر، تم الإلغاء.")
                    return
            
            self.x_client.create_tweet(text=text)
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
            logging.info("🚀 تم النشر بنجاح!")
        except Exception as e: logging.error(f"❌ خطأ نشر: {e}")

    def notify_wa(self, msg):
        if self.has_wa:
            try: self.wa_client.messages.create(from_='whatsapp:+14155238886', body=f"🤖 *أيبكس:* {msg}", to=f"whatsapp:{os.getenv('MY_PHONE_NUMBER')}")
            except: pass

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.handle_mentions()
    time.sleep(random.randint(10, 30)) # فاصل قصير بين المهام
    bot.run_scoop_mission()
