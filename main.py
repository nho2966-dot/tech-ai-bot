import os, sqlite3, logging, hashlib, time, re, random
import tweepy, feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "news.db"

# الدليل التحريري (بناءً على طلبك: تقني، عربي، مصطلحات إنجليزية بين قوسين)
AUTHORITY_PROMPT = """
أنت رئيس تحرير (TechElite). صُغ المحتوى بناءً على [النوع الإلزامي].
القواعد: 
1. التزام تام بالحقائق، نبرة باردة ورصينة.
2. المصطلحات الإنجليزية بين قوسين مثل (Artificial Intelligence).
3. تجنب اقتطاع التغريدات، النشر باللغة العربية فقط.
4. التنسيق: ابدأ بـ [TWEET_1] ثم المحتوى، ثم [TWEET_2] وهكذا.
"""

class TechEliteAuthority:
    AR_STOP = {"من", "في", "على", "إلى", "عن", "تم", "كما", "وفق", "حيث", "بعد"}
    SOURCE_TRUST = {"theverge.com": "موثوق", "9to5mac.com": "موثوق", "techcrunch.com": "موثوق"}

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
        # إعداد X
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        # إعداد OpenRouter (كبديل مستقر لـ Gemini)
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def _generate_ai(self, prompt, context):
        try:
            response = self.ai_client.chat.completions.create(
                model="alibi/qwen-2.5-72b-instruct", # نموذج قوي جداً في العربية
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": context}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"⚠️ AI Error: {e}")
            return None

    def pre_classify(self, title):
        t = title.lower()
        if any(x in t for x in ["launch", "announce"]): return "إطلاق"
        if any(x in t for x in ["leak", "rumor"]): return "تسريب"
        return "تقرير تقني"

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
                
                reply = self._generate_ai("رد كخبير تقني سعودي بلهجة بيضاء رصينة ومختصرة جداً.", tweet.text)
                if reply:
                    self.x_client.create_tweet(text=reply[:278], in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, "reply", datetime.now().isoformat()))
                    conn.commit()
            conn.close()
        except Exception as e: logging.error(f"Reply Error: {e}")

    def post_authority_thread(self, ai_text, url, domain, news_type):
        blocks = self._parse_blocks(ai_text)
        content_tweets = [blocks[k] for k in ["TWEET_1", "TWEET_2"] if k in blocks]
        
        footer = f"🛡️ رصد: {news_type}\n🔗 {url}\n—\n🧠 TechElite"
        all_tweets = content_tweets + [footer]
        
        last_id = None
        for t in all_tweets:
            try:
                res = self.x_client.create_tweet(text=t[:278], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(10)
            except Exception: break
        return True

    def run_cycle(self):
        # 1. الردود الذكية أولاً
        self.handle_smart_replies()
        
        # 2. النشر الاستهدافي
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/"]
        for url in sources:
            feed = feedparser.parse(url)
            for e in feed.entries[:2]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    news_type = self.pre_classify(e.title)
                    content = self._generate_ai(AUTHORITY_PROMPT.replace("[نوع]", news_type), e.title)
                    if content and self.post_authority_thread(content, e.link, url, news_type):
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
