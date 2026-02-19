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
from tenacity import retry, stop_after_attempt, wait_exponential

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format="🛡️ [إمبراطورية ناصر]: %(message)s")

# --- Constants ---
MAX_TWEET_LENGTH = 600
MAX_DAILY_POSTS = 5
MAX_RETRIES = 3
DELAY_MIN = 40
DELAY_MAX = 90

# --- 1. رادار البحث عن الإعدادات ---
def _find_and_load_config():
    root_dir = pathlib.Path(__file__).parent.parent if "__file__" in locals() else pathlib.Path.cwd()
    config_path = next(root_dir.glob("**/config.yaml"), None)
    if not config_path:
        raise FileNotFoundError("❌ ملف config.yaml مفقود!")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class NasserApexBot:
    def __init__(self):
        self.config = _find_and_load_config()
        self._init_db()
        self._init_clients()
        self.recent_posts = deque(maxlen=15)
        self.used_topics = deque(maxlen=5)
        self.daily_posts = 0
        self.today = date.today().isoformat()
        print(f"✅ تم التشغيل: {self.config['logging']['name']}")

    # --- 2. تهيئة قاعدة البيانات ---
    def _init_db(self):
        db_path = self.config['bot']['database_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied (id TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_posts (day TEXT PRIMARY KEY, count INTEGER)")

    # --- 3. تهيئة العملاء (Clients) ---
    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

        self.has_wa = False
        if self.config['bot'].get('wa_notify'):
            try:
                from twilio.rest import Client
                self.wa_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
                self.has_wa = True
            except Exception as e:
                logging.warning(f"⚠️ الواتساب معطل: {e}")

        # مصفوفة العقول الستة (The 6 Brains)
        self.brains = {
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"),
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "Gemini": self.gemini_client
        }

    # --- 4. محرك التوليد متعدد العقول مع منع الهلوسة ---
    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=15))
    def generate_content(self, mode_key, content_input=""):
        system_core = self.config['prompts']['system_core']
        mode_prompt = self.config['prompts']['modes'][mode_key].format(content=content_input)
        full_prompt = f"{system_core}\n\nالمهمة: {mode_prompt}"

        for model_cfg in self.config['models']['priority']:
            try:
                api_key = os.getenv(model_cfg['env_key'])
                if not api_key: continue

                if model_cfg['type'] == "google":
                    c = genai.Client(api_key=api_key)
                    res = c.models.generate_content(model=model_cfg['model'], contents=full_prompt)
                    return self.finalize_text(res.text)
                elif model_cfg['type'] in ["openai", "xai", "groq", "openrouter"]:
                    urls = {"xai": "https://api.x.ai/v1", "groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
                    c = OpenAI(api_key=api_key, base_url=urls.get(model_cfg['type']))
                    res = c.chat.completions.create(model=model_cfg['model'], messages=[{"role": "user", "content": full_prompt}])
                    return self.finalize_text(res.choices[0].message.content)
            except Exception as e:
                logging.warning(f"⚠️ {model_cfg['name']} فشل: {str(e)[:50]}")
                continue
        return None

    # --- 5. الجراح (منع الهلوسة والاقتطاع وتنظيف) ---
    def finalize_text(self, text):
        if not text or len(text.strip()) < 30: return None

        # تنظيف البدايات المملة والهلوسة
        blacklist = ["أعتذر", "لا يوجد", "حسناً", "دعنا", "خلاصة القول", "المرسل", "تخطي", "ربما", "يُعتقد"]
        if any(x in text for x in blacklist): return None

        # تنظيف من الرموز والأسطر الزائدة
        clean_text = text.replace("\n", " ").strip()

        if len(clean_text) <= MAX_TWEET_LENGTH:
            return clean_text

        # إذا طويلة، ابحث عن آخر نقطة لضمان اكتمال المعنى
        truncated = clean_text[:MAX_TWEET_LENGTH - 3]
        last_stop = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('؟'))

        if last_stop > 150:
            return truncated[:last_stop + 1] + "..."

        logging.warning("⚠️ نص مقتطع.. تم الإلغاء للحفاظ على الهيبة.")
        return None

    # --- 6. الردود الذكية ---
    def handle_mentions(self):
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
                    time.sleep(random.randint(DELAY_MIN, DELAY_MAX))
        except Exception as e:
            logging.error(f"⚠️ خطأ ردود: {e}")

    # --- 7. السكوبات العميقة (Deep Scraper) ---
    def run_scoop_mission(self):
        logging.info("🔍 رصد السكوبات...")
        for feed_cfg in self.config['sources']['rss_feeds']:
            feed = feedparser.parse(feed_cfg['url'])
            if not feed.entries: continue

            entry = feed.entries[0]
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM processed WHERE id=?", (entry.link,)).fetchone(): continue

            try:
                res = requests.get(entry.link, headers={"User-Agent": self.config['bot']['user_agent']}, timeout=10)
                soup = BeautifulSoup(res.content, "html.parser")
                paragraphs = [p.get_text() for p in soup.find_all('p') if len(p.get_text()) > 80]
                article_body = " ".join(paragraphs[:5])

                if len(article_body) < 350: continue

                tweet = self.finalize_text(self.generate_content("POST_DEEP", article_body))
                if tweet:
                    self.publish(tweet)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO processed VALUES (?, CURRENT_TIMESTAMP)", (entry.link,))
                    self.notify_wa(f"✅ نُشر سكوب: {entry.title}")
                    break
            except Exception as e:
                logging.warning(f"⚠️ خطأ في سكوب {entry.link}: {e}")

    # --- 8. النشر الآمن ---
    def publish(self, text):
        if not text or self.daily_posts >= MAX_DAILY_POSTS:
            logging.info("⚠️ الحد اليومي وصل أو النص فارغ")
            return

        try:
            h = hashlib.sha256(text.encode()).hexdigest()
            self.x_client.create_tweet(text=text[:MAX_TWEET_LENGTH])
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
            self.daily_posts += 1
            logging.info("✅ تم النشر بنجاح!")
        except tweepy.TooManyRequests:
            logging.warning("429 Rate Limit → تأخير وإعادة المحاولة لاحقًا")
            time.sleep(900)  # 15 دقيقة
        except Exception as e:
            logging.error(f"❌ خطأ نشر: {e}")

    # --- 9. إشعار واتساب ---
    def notify_wa(self, msg):
        if self.has_wa:
            try:
                self.wa_client.messages.create(
                    from_='whatsapp:+14155238886',
                    body=f"🤖 *أيبكس:* {msg}",
                    to=f"whatsapp:{os.getenv('MY_PHONE_NUMBER')}"
                )
            except Exception as e:
                logging.warning(f"⚠️ فشل إشعار واتساب: {e}")

    def run(self):
        self.handle_mentions()
        time.sleep(random.randint(300, 600))
        self.run_scoop_mission()

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.run()
