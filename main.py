import os, sqlite3, logging, hashlib, time, re, random, requests
import tweepy, feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()
DB_FILE = "news.db"

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
        conn.execute("CREATE TABLE IF NOT EXISTS decisions (hash TEXT PRIMARY KEY, decision TEXT, reason TEXT, timestamp TEXT)")
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
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")

    def fact_overlap_guard(self, ai_text, source_text):
        ai_words = set(re.findall(r'\w+', ai_text.lower())) - self.AR_STOP
        src_words = set(re.findall(r'\w+', source_text.lower())) - self.AR_STOP
        if not ai_words: return True
        diff = len(ai_words - src_words) / len(ai_words)
        return diff < 0.20

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

    def handle_engagement_polls(self):
        try:
            conn = sqlite3.connect(DB_FILE)
            last = conn.execute("SELECT title FROM news WHERE hash NOT LIKE 'rep_%' ORDER BY published_at DESC LIMIT 1").fetchone()
            conn.close()
            if not last: return
            prompt = f"بناءً على الخبر: ({last[0]})\nصُغ سؤال استطلاع رأي تقني محايد مع 3 خيارات قصيرة جداً.\nالتنسيق: السؤال في سطر والخيارات في الأسطر التالية."
            res = self._generate_ai(prompt, "Engagement Engine")
            if res:
                lines = [l.strip() for l in res.strip().split('\n') if l.strip()]
                if len(lines) >= 4:
                    self.x_client.create_tweet(text=f"📊 استطلاع TechElite | {lines[0]}", poll_options=lines[1:4], poll_duration_minutes=1440)
        except Exception as e: logging.error(f"Poll Error: {e}")

    def post_authority_thread(self, ai_text, url, domain, source_text, news_type):
        if not self.fact_overlap_guard(ai_text, source_text): return False
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
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/", "https://bloomberg.com/feeds/technology/rss"]
        random.shuffle(sources)
        for url in sources:
            domain = re.findall(r'https?://([^/]+)', url)[0].replace("www.", "")
            feed = feedparser.parse(url)
            for e in feed.entries[:3]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                desc = getattr(e, 'description', getattr(e, 'summary', ''))
                if len(desc.split()) < 40 or self.is_recycled_news(e.title): continue
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    news_type = self.pre_classify(e.title)
                    content = self._generate_ai(f"{AUTHORITY_PROMPT}\n[TYPE]: {news_type}", f"Title: {e.title}\nDesc: {desc}")
                    if content and self.post_authority_thread(content, e.link, domain, desc, news_type):
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        self.handle_engagement_polls()
                        return
                conn.close()

    def is_recycled_news(self, title):
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT title FROM news WHERE published_at > ?", ((datetime.now() - timedelta(days=2)).isoformat(),)).fetchall()
        conn.close()
        new_kw = set(re.findall(r'\w+', title.lower())) - self.STOPWORDS
        for (old,) in rows:
            old_kw = set(re.findall(r'\w+', old.lower())) - self.STOPWORDS
            if len(new_kw & old_kw & self.CORE_TERMS) >= 2: return True
        return False

    def _generate_ai(self, prompt, context):
        try:
            # التعديل الحاسم هنا لمواكبة الـ SDK الجديد
            res = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=f"{prompt}\n\n{context}"
            )
            return res.text
        except Exception as e:
            logging.error(f"⚠️ Gemini Error: {e}")
            return None

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
