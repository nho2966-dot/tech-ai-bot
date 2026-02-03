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
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")

    def run_cycle(self):
        # مصادر تقنية متنوعة لضمان شمولية البحث
        sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5mac.com/feed/",
            "https://www.macrumors.com/macrumors.xml",
            "https://techcrunch.com/feed/"
        ]
        random.shuffle(sources)
        
        for url in sources:
            feed = feedparser.parse(url)
            # فحص آخر 15 خبر للعثور على الأنسب
            for e in feed.entries[:15]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    # التركيز على التوجهات التقنية (AI, Apple, Nvidia, Chips)
                    if any(w in e.title.lower() for w in ["apple", "nvidia", "ai", "tesla", "leak", "m4", "m5", "openai"]):
                        
                        prompt = "أنت محرر تقني نخبوي. حلل هذا الخبر وصغ ثريد بلهجة سعودية بيضاء فخمة. ركز على الجانب التقني العميق والمستقبلي. اجعله 3 نقاط مركزة جداً."
                        
                        try:
                            res = self.gemini_client.models.generate_content(model='gemini-1.5-flash', contents=f"{prompt}\n\n{e.title}")
                            ai_text = res.text
                        except:
                            res = self.ai_qwen.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role":"user","content":f"{prompt}\n\n{e.title}"}])
                            ai_text = res.choices[0].message.content
                        
                        if ai_text and self.post_thread(ai_text, e.title):
                            conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                            conn.commit()
                            conn.close()
                            return # نشر خبر واحد فقط لكل فترة ذروة
                conn.close()

    def post_thread(self, content, title):
        tweets = [t.strip() for t in re.split(r'\n\s*\d+[\/\.\)]\s*|\n\n', content.strip()) if len(t.strip()) > 15]
        max_tweets = tweets[:3] # ثريد قصير جداً (3 تغريدات) لراحة المتابع
        
        last_id = None
        for i, tweet in enumerate(max_tweets):
            text = f"{i+1}/ {tweet}"
            if i == len(max_tweets) - 1:
                text += "\n\n#تقنية #سبق_تقني"
            
            if len(text) > 280: text = text[:277] + "..."
            
            try:
                res = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=last_id)
                last_id = res.data['id']
                time.sleep(5)
            except: break
        return True

if __name__ == "__main__":
    TechEliteBot().run_cycle()
