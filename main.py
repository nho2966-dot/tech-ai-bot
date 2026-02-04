import os, sqlite3, logging, hashlib, time, re, random
import tweepy, feedparser
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "news.db"

STRICT_FRIENDLY_PROMPT = """
أنت رئيس تحرير (TechElite)، خبير تقني ودود. صُغ ثريداً ممتعاً ورصيناً بالعربية بناءً على النص.
القواعد:
1. يمنع تماماً أي رموز صينية أو لغات غير مفهومة.
2. استخدم لغة ودودة وسلسة مع وضع المصطلح التقني بالإنجليزية بين قوسين (Term).
3. التنسيق:
[TWEET_1]: افتتاحية جذابة تشرح الخبر الأساسي.
[TWEET_2]: تفاصيل تقنية (Technical Specs) مبسطة.
[POLL_QUESTION]: سؤال استطلاع رأي (Poll) ذكي (أقل من 80 حرفاً).
[POLL_OPTIONS]: خياران أو 3 خيارات، مفصولة بشرطة (مثلاً: رائع جداً - لا أحتاجه).
"""

class TechEliteFinal:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.commit(); conn.close()

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_clean_text(self, text):
        if re.search(r'[\u4e00-\u9fff]', text): return False
        return True

    def _generate_ai(self, context):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":STRICT_FRIENDLY_PROMPT},{"role":"user","content":context}],
                temperature=0.1
            )
            content = r.choices[0].message.content.strip()
            return content if self._is_clean_text(content) else None
        except: return None

    def post_thread(self, ai_text, url):
        t1 = re.search(r'\[TWEET_1\](.*?)(?=\[|$)', ai_text, re.S)
        t2 = re.search(r'\[TWEET_2\](.*?)(?=\[|$)', ai_text, re.S)
        p_q = re.search(r'\[POLL_QUESTION\](.*?)(?=\[|$)', ai_text, re.S)
        p_o = re.search(r'\[POLL_OPTIONS\](.*?)(?=\[|$)', ai_text, re.S)

        if not (t1 and t2 and p_q and p_o): return False

        tweets_data = [
            {"text": f"1/ {t1.group(1).strip()}"[:278]},
            {"text": f"2/ {t2.group(1).strip()}\n\n🔗 المصدر: {url}"[:278]},
            {"text": f"3/ رأيكم يهمنا: {p_q.group(1).strip()}"[:278], "is_poll": True}
        ]

        last_id = None
        for i, item in enumerate(tweets_data):
            retries = 0
            while retries < 3:
                try:
                    if item.get("is_poll"):
                        options = [o.strip() for o in p_o.group(1).split('-') if o.strip()][:4]
                        res = self.x_client.create_tweet(text=item["text"], poll_options=options, poll_duration_minutes=1440, in_reply_to_tweet_id=last_id)
                    else:
                        res = self.x_client.create_tweet(text=item["text"], in_reply_to_tweet_id=last_id)
                    
                    last_id = res.data["id"]
                    time.sleep(40) # زيادة الفاصل الزمني للأمان
                    break
                except tweepy.TooManyRequests:
                    retries += 1
                    wait = 120 * retries
                    logging.warning(f"⚠️ ضغط عالي، انتظار {wait} ثانية...")
                    time.sleep(wait)
                except Exception as e:
                    logging.error(f"❌ خطأ: {e}"); return False
        return True

    def run_cycle(self):
        SOURCES = [
            "https://venturebeat.com/category/ai/feed/", "https://openai.com/news/rss.xml",
            "https://9to5mac.com/feed/", "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml", "https://www.bleepingcomputer.com/feed/"
        ]
        random.shuffle(SOURCES)
        published = 0
        for url in SOURCES:
            if published >= 3: break
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                if published >= 3: break
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    ai_text = self._generate_ai(f"Title: {e.title}\nSummary: {getattr(e, 'summary', '')}")
                    if ai_text and self.post_thread(ai_text, e.link):
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit(); published += 1
                        time.sleep(1200) # انتظار 20 دقيقة بين ثريد وآخر
                conn.close()

if __name__ == "__main__":
    TechEliteFinal().run_cycle()
