import os, sqlite3, logging, hashlib, time, re, random
import tweepy, feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "news.db"

# هندسة الأوامر لمنع الهلوسة والالتزام باللغة العربية والمصطلحات الإنجليزية
STRICT_AUTHORITY_PROMPT = """
أنت محرر تقني في (TechElite). صُغ ثريداً تقنياً دقيقاً باللغة العربية بناءً على النص المرفق فقط.
القواعد الصارمة:
1. يمنع إضافة أي معلومة (أرقام، تواريخ، أسماء) غير موجودة في النص.
2. المصطلحات التقنية تكتب بالإنجليزية بين قوسين (Term) بجانب معناها العربي.
3. تجنب الاقتطاع؛ وزع المحتوى على التنسيق التالي:

[TWEET_1]: المعلومة المركزية للخبر بأسلوب "خطاف" رصين وجذاب.
[TWEET_2]: تفاصيل تقنية حرفية مترجمة من النص (أرقام، ميزات).
[TWEET_3]: سؤال تقني تفاعلي للمتابعين مشتق من محتوى الخبر فقط.
"""

class TechEliteAuthority:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()
        self.my_id = None

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            hash TEXT PRIMARY KEY,
            title TEXT,
            published_at TEXT
        )
        """)
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
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def _generate_ai(self, prompt, context):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":prompt},{"role":"user","content":context}],
                temperature=0.1, # صرامة تامة ضد الهلوسة
                max_tokens=700
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def is_recycled_news(self, title):
        conn = sqlite3.connect(DB_FILE)
        # فحص الأخبار في آخر يومين لمنع التكرار
        cutoff = (datetime.now() - timedelta(days=2)).isoformat()
        rows = conn.execute("SELECT title FROM news WHERE published_at > ?", (cutoff,)).fetchall()
        conn.close()
        
        t_clean = re.sub(r'\W+', '', title.lower())
        for (old_title,) in rows:
            if re.sub(r'\W+', '', old_title.lower()) == t_clean:
                return True
        return False

    def post_thread(self, ai_text, url):
        blocks = {}
        current = None
        for line in ai_text.splitlines():
            if line.startswith("[TWEET_"):
                current = line.split("]")[0].strip("[]")
                blocks[current] = []
            elif current and line.strip():
                blocks[current].append(line.strip())
        
        tweets = [" ".join(blocks[k]) for k in ["TWEET_1", "TWEET_2", "TWEET_3"] if k in blocks]
        if not tweets: return False

        footer = f"🔗 المصدر:\n{url}\n\n🛡️ رصد TechElite"
        tweets.append(footer)

        last_id = None
        for i, t in enumerate(tweets):
            try:
                prefix = f"{i+1}/ " if i < len(tweets)-1 else ""
                res = self.x_client.create_tweet(text=f"{prefix}{t}"[:278], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(15) # فاصل بين التغريدات
            except Exception as e:
                logging.error(f"Tweet Error: {e}")
                break
        return True

    def handle_mentions(self):
        try:
            if not self.my_id:
                self.my_id = str(self.x_client.get_me().data.id)
            mentions = self.x_client.get_users_mentions(id=self.my_id, max_results=5)
            if not mentions.data: return

            conn = sqlite3.connect(DB_FILE)
            for tweet in mentions.data:
                h = f"reply_{tweet.id}"
                if conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone(): continue
                
                reply_text = self._generate_ai("أنت خبير تقني رصين. رد على الاستفسار المرفق بوقار ودون هلوسة وباختصار.", tweet.text)
                if reply_text:
                    self.x_client.create_tweet(text=reply_text[:278], in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, "reply", datetime.now().isoformat()))
                    conn.commit()
            conn.close()
        except Exception as e: logging.error(f"Mentions Error: {e}")

    def run_cycle(self):
        self.handle_mentions()
        
        count = 0
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/", "https://techcrunch.com/feed/"]
        random.shuffle(sources)

        for url in sources:
            if count >= 2: break
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                if count >= 2: break
                
                if self.is_recycled_news(e.title): continue
                
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    # إرسال العنوان والوصف لضمان الدقة
                    context = f"Title: {e.title}\nDetails: {getattr(e, 'summary', '')}"
                    ai_content = self._generate_ai(STRICT_AUTHORITY_PROMPT, context)
                    
                    if ai_content and self.post_thread(ai_content, e.link):
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit()
                        count += 1
                        time.sleep(60) # فاصل بين الخبرين
                conn.close()

if __name__ == "__main__":
    TechEliteAuthority().run_cycle()
