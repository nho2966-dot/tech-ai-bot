import os, sqlite3, logging, hashlib, time, re, random, requests
import tweepy, feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()
DB_FILE = "news.db"

# 1️⃣ الدليل التحريري الصارم (الموحد)
AUTHORITY_PROMPT = """
أنت رئيس تحرير في وكالة (TechElite). صُغ الثريد بناءً على [النوع الإلزامي] المرفق.
القواعد: ممنوع الاستنتاج، ممنوع صفات المدح، التزام تام بالحقائق، النبرة باردة ورصينة.
"""

class TechEliteEnterprise:
    STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "new", "update", "report"}
    AR_STOP = {"من", "في", "على", "إلى", "عن", "تم", "كما", "وفق", "حيث", "بعد", "هذا", "خلال"}
    CORE_TERMS = {"ai", "chip", "gpu", "ios", "android", "iphone", "nvidia", "m4", "snapdragon", "openai"}
    SOURCE_TRUST = {"theverge.com": "موثوق", "9to5mac.com": "موثوق", "techcrunch.com": "موثوق", "bloomberg.com": "عالي الموثوقية"}

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()
        self.my_id = None

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        # جدول الأخبار
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        # 1️⃣ سجل القرارات (Audit Log)
        conn.execute("""CREATE TABLE IF NOT EXISTS decisions 
                        (hash TEXT PRIMARY KEY, decision TEXT, reason TEXT, timestamp TEXT)""")
        conn.commit(); conn.close()

    def _init_clients(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        auth = tweepy.OAuth1UserHandler(os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"), os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET"))
        self.x_api_v1 = tweepy.API(auth)
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")

    def log_decision(self, h, decision, reason):
        """تسجيل سجل التدقيق (Audit Log) لغايات الحوكمة"""
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?)", 
                     (h, decision, reason, datetime.now().isoformat()))
        conn.commit(); conn.close()

    def fact_overlap_guard(self, ai_text, source_text):
        ai_words = set(re.findall(r'\w+', ai_text.lower())) - self.AR_STOP
        src_words = set(re.findall(r'\w+', source_text.lower())) - self.AR_STOP
        diff = len(ai_words - src_words) / max(len(ai_words), 1)
        return diff < 0.20

    def pre_classify(self, title):
        t = title.lower()
        if any(x in t for x in ["launch", "announce", "reveal"]): return "إطلاق"
        if any(x in t for x in ["update", "version", "ios"]): return "تحديث"
        if any(x in t for x in ["leak", "rumor", "spotted"]): return "تسريب"
        return "تقرير"

    def run_cycle(self):
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/", "https://bloomberg.com/feeds/technology/rss"]
        random.shuffle(sources)
        
        for url in sources:
            domain = re.findall(r'https?://([^/]+)', url)[0].replace("www.", "")
            feed = feedparser.parse(url)
            
            for e in feed.entries[:3]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                
                # 2️⃣ الاكتفاء المعلوماتي
                if len(e.description.split()) < 40:
                    self.log_decision(h, "REJECTED", "Insufficient information (Under 40 words)")
                    continue
                
                if self.is_recycled_news(e.title):
                    self.log_decision(h, "REJECTED", "Recycled/Duplicate News")
                    continue
                
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    news_type = self.pre_classify(e.title)
                    hard_trust = self.SOURCE_TRUST.get(domain, "متوسط")
                    
                    # 3️⃣ بصمة زمنية ذكية (تأخير الإطلاقات لتعزيز مظهر الرصد)
                    if news_type == "إطلاق":
                        logging.info("⏳ Smart Delay: Waiting 15m for authority look...")
                        # في GitHub Actions، يمكننا فقط المتابعة، ولكن المنطق متاح للجدولة

                    clean_context = f"Title: {e.title}\nDescription: {e.description}"
                    content = self._generate_ai(f"{AUTHORITY_PROMPT}\n[TYPE]: {news_type}", clean_context)
                    
                    if content and self.post_authority_thread(content, e.link, domain, clean_context, news_type):
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit(); conn.close()
                        self.log_decision(h, "PUBLISHED", f"Type: {news_type}, Source: {domain}")
                        return
                conn.close()

    def post_authority_thread(self, ai_text, url, domain, source_text, news_type):
        if not self.fact_overlap_guard(ai_text, source_text):
            self.log_decision(hashlib.sha256(url.encode()).hexdigest(), "REJECTED", "Failed Fact Overlap Guard (Hallucination risk)")
            return False

        blocks = self._parse_blocks(ai_text)
        content_tweets = [blocks[k] for k in ["TWEET_1", "TWEET_2", "TWEET_3"] if k in blocks]

        footer = f"🛡️ رصد تقني موثّق\n- المصدر: {self.SOURCE_TRUST.get(domain)}\n- الصنف: {news_type}\n—\n🧠 TechElite | رصد بلا تضخيم"
        all_tweets = content_tweets[:3] + [footer + f"\n🔗 {url}"]

        last_id = None
        for t in all_tweets:
            try:
                res = self.x_client.create_tweet(text=t[:278], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(12)
            except: break
        return True

    def is_recycled_news(self, title):
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT title FROM news WHERE published_at > ?", ((datetime.now() - timedelta(days=2)).isoformat(),)).fetchall()
        conn.close()
        new_kw = set(re.findall(r'\w+', title.lower())) - self.STOPWORDS
        for (old,) in rows:
            old_kw = set(re.findall(r'\w+', old.lower())) - self.STOPWORDS
            if len(new_kw & old_kw & self.CORE_TERMS) >= 2 or (len(new_kw | old_kw) > 0 and len(new_kw & old_kw)/len(new_kw | old_kw) > 0.65):
                return True
        return False

    def _generate_ai(self, prompt, context):
        try:
            res = self.gemini_client.models.generate_content(model='gemini-1.5-flash', contents=f"{prompt}\n\n{context}")
            return res.text
        except: return None

    def _parse_blocks(self, text):
        blocks, current = {}, None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current = line.strip("[]"); blocks[current] = []
            elif current and line: blocks[current].append(line)
        return {k: " ".join(v) for k, v in blocks.items()}

if __name__ == "__main__":
    TechEliteEnterprise().run_cycle()
