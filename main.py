import os
import time
import logging
import feedparser
import tweepy
import sqlite3
from datetime import datetime
from google import genai
from openai import OpenAI as OpenAIClient

# --- إعداد اللوج والسيادة ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(levelname)s] | %(message)s")
logger = logging.getLogger("Sovereign_Ultimate")

class SovereignAI:
    def __init__(self):
        self.db_path = "sovereign_memory.db"
        self._init_db()
        self.providers = {
            "gemini": {"model": "gemini-2.0-flash", "type": "google"},
            "groq": {"model": "llama-3.3-70b-versatile", "type": "openai", "url": "https://api.groq.com/openai/v1"},
            "openai": {"model": "gpt-4o-mini", "type": "openai", "url": None}
        }

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, content TEXT, timestamp DATETIME)")

    def is_duplicate(self, content):
        # منع تكرار المحتوى (Strict Filter)
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT id FROM history WHERE content = ?", (content,)).fetchone()
            return res is not None

    def save_to_memory(self, content):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (content, timestamp) VALUES (?, ?)", (content, datetime.now()))

    def get_key(self, name):
        # يبحث عن المفتاح بأي صيغة (مرونة مطلقة)
        keys = [f"{name.upper()}_KEY", f"X_{name.upper()}_KEY", f"{name.upper()}_API_KEY", f"X_{name.upper()}_API_KEY"]
        for k in keys:
            val = os.getenv(k)
            if val: return val
        return None

    def generate_sovereign_content(self, raw_data):
        sys_msg = (
            "أنت خبير تقني سيادي. ركز على ممارسات Artificial Intelligence and its latest tools "
            "بما ينعكس على الأفراد وتطورهم الشخصي. استخدم لهجة خليجية بيضاء (جلفي راقي). "
            "تجنب الحديث عن المؤسسات أو الشركات. اجعل التغريدة تفاعلية وقصيرة."
        )
        
        for name, cfg in self.providers.items():
            key = self.get_key(name)
            if not key: continue
            
            try:
                logger.info(f"🛡️ محاولة التوليد عبر [{name}]...")
                if cfg["type"] == "google":
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=cfg["model"], 
                        contents=raw_data, 
                        config={'system_instruction': sys_msg}
                    ).text.strip()
                else:
                    client = OpenAIClient(api_key=key, base_url=cfg.get("url"))
                    resp = client.chat.completions.create(
                        model=cfg["model"],
                        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": raw_data}]
                    )
                    response = resp.choices[0].message.content.strip()
                
                if response and not self.is_duplicate(response):
                    return response
            except Exception as e:
                logger.error(f"⚠️ فشل {name}: {str(e)[:50]}")
        return None

# --- نظام النشر الفائق ---
def publish_to_x(content):
    try:
        auth = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        auth.create_tweet(text=content)
        logger.info("✅ تم النشر بنجاح سيادي!")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في النشر: {e}")
        return False

# --- المحرك الرئيسي ---
def main():
    # جلب أخبار تقنية متعلقة بالأفراد والذكاء الاصطناعي
    feed = feedparser.parse("https://hnrss.org/newest?q=AI+tools+for+individuals")
    if not feed.entries:
        logger.warning("📭 لا توجد أخبار جديدة حالياً.")
        return

    top_news = f"العنوان: {feed.entries[0].title}\nالملخص: {feed.entries[0].summary}"
    
    ai_engine = SovereignAI()
    sovereign_tweet = ai_engine.generate_sovereign_content(top_news)
    
    if sovereign_tweet:
        if publish_to_x(sovereign_tweet):
            ai_engine.save_to_memory(sovereign_tweet)
    else:
        logger.critical("🚨 تعذر إنتاج محتوى (تحقق من المفاتيح والضغط على السيرفرات)")

if __name__ == "__main__":
    main()
