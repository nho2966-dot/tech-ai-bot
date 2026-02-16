import os
import logging
import feedparser
import tweepy
import sqlite3
from datetime import datetime
from google import genai
from openai import OpenAI as OpenAIClient

# إعدادات اللوج
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(levelname)s] | %(message)s")
logger = logging.getLogger("Sovereign_X")

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
            conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, content TEXT, tweet_id TEXT, timestamp DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS processed_mentions (mention_id TEXT PRIMARY KEY)")

    def get_key(self, name):
        keys = [f"{name.upper()}_KEY", f"X_{name.upper()}_KEY", f"{name.upper()}_API_KEY", f"X_{name.upper()}_API_KEY"]
        for k in keys:
            val = os.getenv(k)
            if val: return val
        return None

    def ask_ai(self, prompt, is_reply=False):
        sys_msg = (
            "أنت خبير تقني خليجي. ركز على Artificial Intelligence and its latest tools للأفراد. "
            "اللهجة: خليجية بيضاء واضحة. "
            "في الردود: كن ودوداً، مختصراً، وساعد الشخص في سؤاله التقني."
        )
        if is_reply: sys_msg += " (أنت الآن ترد على منشن، اجعل الرد شخصي ومباشر)."

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
                logger.error(f"⚠️ فشل {name}: {e}")
        return None

# --- محرك تويتر (X) الجديد ---
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
        self.me = self.client.get_me().data

    def handle_mentions(self, ai_engine):
        # جلب المنشنز الأخيرة
        mentions = self.client.get_users_mentions(self.me.id)
        if not mentions.data: return

        with sqlite3.connect(ai_engine.db_path) as conn:
            for tweet in mentions.data:
                # التأكد أننا لم نرد عليه من قبل (Strict Filter)
                res = conn.execute("SELECT mention_id FROM processed_mentions WHERE mention_id = ?", (tweet.id,)).fetchone()
                if res: continue

                logger.info(f"💬 معالجة منشن من: {tweet.text}")
                reply_text = ai_engine.ask_ai(tweet.text, is_reply=True)
                
                if reply_text:
                    self.client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO processed_mentions (mention_id) VALUES (?)", (tweet.id,))
                    logger.info("✅ تم الرد بنجاح!")

    def publish_news(self, ai_engine):
        sources = ["https://hnrss.org/newest?q=AI+tools+for+individuals", "https://www.theverge.com/ai/rss/index.xml"]
        for url in sources:
            feed = feedparser.parse(url)
            if feed.entries:
                news = f"حلل للأفراد: {feed.entries[0].title}"
                content = ai_engine.ask_ai(news)
                if content:
                    self.client.create_tweet(text=content)
                    logger.info("✅ تم نشر تغريدة إخبارية!")
                    break

def main():
    ai = SovereignAI()
    x = XManager()
    
    # 1. الرد على المنشنز أولاً لتعزيز التفاعل
    x.handle_mentions(ai)
    
    # 2. نشر محتوى جديد
    x.handle_mentions(ai) # فحص مزدوج للردود
    x.publish_news(ai)

if __name__ == "__main__":
    main()
