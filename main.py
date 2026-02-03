import os, sqlite3, logging, hashlib, time, re, random
import tweepy, feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()
DB_FILE = "news.db"

# الدليل التحريري
AUTHORITY_PROMPT = """
أنت رئيس تحرير في وكالة (TechElite). صُغ المحتوى بناءً على [النوع الإلزامي] المرفق.
القواعد: ممنوع الاستنتاج، ممنوع صفات المدح، التزام تام بالحقائق، النبرة باردة ورصينة، المصطلحات الإنجليزية بين قوسين (Term).
تجنب اقتطاع التغريدات، والتزم بالنشر باللغة العربية حصراً.
"""

class TechEliteAuthority:
    STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "new", "update", "report"}
    AR_STOP = {"من", "في", "على", "إلى", "عن", "تم", "كما", "وفق", "حيث", "بعد", "هذا", "خلال", "بناء"}
    CORE_TERMS = {"ai", "chip", "gpu", "ios", "android", "iphone", "nvidia", "m4", "snapdragon", "openai"}
    SOURCE_TRUST = {"theverge.com": "موثوق", "9to5mac.com": "موثوق", "techcrunch.com": "موثوق", "bloomberg.com": "عالي الموثوقية"}
    MAX_TWEETS_BY_TYPE = {"إطلاق": 3, "تحديث": 2, "تسريب": 2, "تقرير": 2}

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()
        self.my_id = None

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.commit()
        conn.close()

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    def _generate_ai(self, prompt, context):
        try:
            # استخدام المسمى المباشر للموديل
            res = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=f"{prompt}\n\n{context}"
            )
            return res.text
        except Exception as e:
            logging.error(f"⚠️ Gemini Error: {e}")
            return None

    def pre_classify(self, title):
        t = title.lower()
        if any(x in t for x in ["launch", "announce", "reveal"]): return "إطلاق"
        if any(x in t for x in ["update", "version", "ios", "beta"]): return "تحديث"
        if any(x in t for x in ["leak", "rumor", "spotted"]): return "تسريب"
        return "تقرير"

    def handle_smart_replies(self):
        try:
            if not self.my_id:
                me = self.x_client.get_me()
                self.my_id = str(me.data.id)
            mentions = self.x_client.get_users_mentions(id=self.my_id, max_results=5)
            if not mentions or not mentions.data: return
            conn = sqlite3.connect(DB_FILE)
            for tweet in mentions.data:
                h = f"rep_{tweet.id}"
                if conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone(): continue
                prompt = "أنت خبير تقني سعودي. رد بلهجة بيضاء رصينة ومختصرة جداً. ممنوع الهلوسة والتزم بالعربية."
                reply = self._generate_ai(prompt, f"استفسار المتابع: {tweet.text}")
                if reply:
                    self.x_client.create_tweet(text=reply[:278], in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, "reply", datetime.now().isoformat()))
                    conn.commit()
            conn.close()
        except Exception as e: logging.error(f"Reply Error: {e}")

    def post_authority_thread(self, ai_text, url, domain, source_text, news_type):
        blocks = self._parse_blocks(ai_text)
        limit = self.MAX_TWEETS_BY_TYPE.get(news_type, 2)
        content_keys = ["TWEET_1", "TWEET_2", "TWEET_3"]
        content_tweets = [blocks[k] for k in content_keys if k in blocks][:limit]
        footer = f"🛡️ رصد تقني موثّق\n- المصدر: {self.SOURCE_TRUST.get(domain, 'متوسط')}\n- الصنف: {news_type}\n—\n🧠 TechElite | رصد بلا تضخيم"
        all_tweets = content_tweets + [footer + f"\n🔗 {url}"]
        last_id = None
        for t in all_tweets:
            try:
                res = self.x_client.create_tweet(text=t[:278], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(12)
            except Exception: break
        return True

    def run_cycle(self):
        self.handle_smart_replies()
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/", "https://techcrunch.com/feed/"]
        random.shuffle(sources)
        for url in sources:
            domain = re.findall(r'https?://([^/]+)', url)[0].replace("www.", "")
            feed = feedparser.parse(url)
            for e in feed.entries[:3]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                desc = getattr(e, 'description', getattr(e, 'summary', ''))
                if len(desc.split()) < 40: continue
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    news_type = self.pre_classify(e.title)
                    content = self._generate_ai(f"{AUTHORITY_PROMPT}\n[TYPE]: {news_type}", f"Title: {e.title}\nDesc: {desc}")
                    if content and self.post_authority_thread(content, e.link, domain, desc, news_type):
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        return
                conn.close()

    def _parse_blocks(self, text):
        blocks, current = {}, None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current = line.strip("[]")
                blocks[current] = []
            elif current and line:
                blocks[current].append(line)
        return {k: " ".join(v) for k, v in blocks.items()}

if __name__ == "__main__":
    TechEliteAuthority().run_cycle()
