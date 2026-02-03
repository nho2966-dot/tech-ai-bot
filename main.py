import os, sqlite3, logging, hashlib, time, re, random
from datetime import datetime, timezone
import tweepy, feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()
DB_FILE = "news.db"

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.commit()
        conn.close()

    def _init_clients(self):
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def extract_hybrid_tags(self, title, description, ai_content=""):
        keywords = {"apple": "#آبل", "iphone": "#آيفون", "nvidia": "#انفيديا", "ai": "#ذكاء_اصطناعي", "tesla": "#تسلا", "leak": "#تسريبات"}
        tags = set(["#تقنية"])
        text = (title + " " + description + " " + (ai_content or "")).lower()
        for k, v in keywords.items():
            if k in text: tags.add(v)
        return " ".join(list(tags)[:6])

    def safe_post(self, text, reply_id=None):
        for i in range(3):
            try:
                res = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=reply_id)
                return res.data['id']
            except tweepy.TooManyRequests:
                time.sleep((i + 1) * 60)
            except Exception as e:
                logging.error(f"❌ Error: {e}")
                break
        return None

    def post_thread(self, content, title, description):
        tweets = [t.strip() for t in re.split(r'\n\s*\d+[\/\.\)]\s*|\n\n', content.strip()) if len(t.strip()) > 10]
        tags = self.extract_hybrid_tags(title, description, content)
        last_id = None
        for i, tweet in enumerate(tweets[:5]):
            prefix = f"{i+1}/ "
            text = prefix + tweet
            if i == len(tweets[:5]) - 1: text += f"\n\n{tags}"
            if len(text) > 280: text = text[:277] + "..."
            last_id = self.safe_post(text, last_id)
            if not last_id: break
            time.sleep(3) # فواصل أمان بين تغريدات الثريد
        return True

    def run_cycle(self):
        sources = [
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "9to5Mac", "url": "https://9to5mac.com/feed/"},
            {"name": "MacRumors", "url": "https://www.macrumors.com/macrumors.xml"}
        ]
        random.shuffle(sources)
        for src in sources:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    # تأكد من وجود كلمات مفتاحية للاستهداف
                    if any(w in e.title.lower() for w in ["apple", "ai", "nvidia", "leak", "tesla", "tsla"]):
                        prompt = "صغ الخبر كثريد تقني نخبوي بلهجة سعودية بيضاء، ركز على المصداقية والسبق."
                        content = None
                        try:
                            res = self.gemini_client.models.generate_content(model='gemini-1.5-flash', contents=f"{prompt}\n\n{e.title}")
                            content = res.text
                        except:
                            res = self.ai_qwen.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role":"user","content":f"{prompt}\n\n{e.title}"}])
                            content = res.choices[0].message.content
                        
                        if content and self.post_thread(content, e.title, e.description):
                            conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                            conn.commit()
                            conn.close()
                            return # أمان: خبر واحد لكل تشغيل
                conn.close()

if __name__ == "__main__":
    TechEliteBot().run_cycle()
