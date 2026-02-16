import os
import logging
import feedparser
import tweepy
import sqlite3
from datetime import datetime
from google import genai
from openai import OpenAI as OpenAIClient

# --- إعدادات النظام السيادي ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(levelname)s] | %(message)s")
logger = logging.getLogger("Sovereign_Final_Engine")

class SovereignAI:
    def __init__(self):
        self.db_path = "sovereign_memory.db"
        self._init_db()
        self.providers = {
            "gemini": {"model": "gemini-2.0-flash", "type": "google"},
            "groq": {"model": "llama-3.3-70b-versatile", "type": "openai", "url": "https://api.groq.com/openai/v1"}
        }

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, content TEXT, timestamp DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS processed_mentions (mention_id TEXT PRIMARY KEY)")

    def get_key(self, name):
        # مرونة جلب المفاتيح حسب التسميات في Secrets
        keys = [f"{name.upper()}_KEY", f"X_{name.upper()}_KEY", f"{name.upper()}_API_KEY", f"X_{name.upper()}_API_KEY"]
        for k in keys:
            val = os.getenv(k)
            if val: return val
        return None

    def ask_ai(self, prompt, is_reply=False):
        # تطبيق كافة الاشتراطات اللغوية والموضوعية
        sys_msg = (
            "أنت خبير تقني سيادي متخصص في Artificial Intelligence and its latest tools. "
            "ركز حصراً على الفوائد والممارسات التي تخدم الأفراد وتطورهم الشخصي. "
            "تجنب تماماً الحديث عن الشركات أو المؤسسات. "
            "اللهجة: خليجية بيضاء راقية. "
            "استبدل أي ذكر لـ 'الثورة الصناعية' بـ 'Artificial Intelligence and its latest tools'."
        )
        if is_reply:
            sys_msg += " (أنت الآن ترد على منشن، اجعل الرد شخصي، ودود، ومختصر جداً)."

        for name, cfg in self.providers.items():
            key = self.get_key(name)
            if not key: continue
            try:
                if cfg["type"] == "google":
                    client = genai.Client(api_key=key)
                    return client.models.generate_content(model=cfg["model"], contents=prompt, config={'system_instruction': sys_msg}).text.strip()
                else:
                    client = OpenAIClient(api_key=key, base_url=cfg.get("url"))
                    resp = client.chat.completions.create(model=cfg["model"], messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}])
                    return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"⚠️ فشل المزود {name}: {e}")
        return None

    def is_duplicate(self, content):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT id FROM history WHERE content = ?", (content,)).fetchone() is not None

    def save_history(self, content):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (content, timestamp) VALUES (?, ?)", (content, datetime.now()))

class XManager:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        try:
            self.me = self.client.get_me().data
        except:
            self.me = None

    def handle_mentions(self, ai_engine):
        if not self.me: return
        mentions = self.client.get_users_mentions(self.me.id)
        if not mentions.data: return

        with sqlite3.connect(ai_engine.db_path) as conn:
            for tweet in mentions.data:
                res = conn.execute("SELECT mention_id FROM processed_mentions WHERE mention_id = ?", (tweet.id,)).fetchone()
                if res: continue

                reply_text = ai_engine.ask_ai(tweet.text, is_reply=True)
                if reply_text:
                    try:
                        self.client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                        conn.execute("INSERT INTO processed_mentions (mention_id) VALUES (?)", (tweet.id,))
                        logger.info(f"✅ تم الرد على المنشن: {tweet.id}")
                    except Exception as e:
                        logger.error(f"❌ خطأ في الرد: {e}")

    def publish_news(self, ai_engine):
        sources = [
            "https://hnrss.org/newest?q=AI+tools+for+individuals",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
        ]
        for url in sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                raw_data = f"حلل للأفراد بلهجة خليجية: {entry.title}\n{entry.summary}"
                content = ai_engine.ask_ai(raw_data)
                
                if content and not ai_engine.is_duplicate(content):
                    try:
                        self.client.create_tweet(text=content)
                        ai_engine.save_history(content)
                        logger.info("✅ تم نشر تغريدة جديدة!")
                        return
                    except Exception as e:
                        logger.error(f"❌ فشل النشر: {e}")

def main():
    ai = SovereignAI()
    x = XManager()
    
    # تنفيذ المهام بالترتيب
    x.handle_mentions(ai)
    x.publish_news(ai)

if __name__ == "__main__":
    main()
