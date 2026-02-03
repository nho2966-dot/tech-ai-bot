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

    def handle_smart_replies(self):
        try:
            me = self.x_client.get_me().data
            mentions = self.x_client.get_users_mentions(id=me.id, max_results=10, expansions=['author_id'])
            if not mentions.data: return

            for tweet in mentions.data:
                if str(tweet.author_id) == str(me.id): continue
                
                conn = sqlite3.connect(DB_FILE)
                if conn.execute("SELECT 1 FROM news WHERE hash=?", (f"rep_{tweet.id}",)).fetchone():
                    conn.close(); continue
                
                prompt = (
                    "أنت خبير تقني سعودي. رد بلهجة بيضاء حيوية ومفيدة. "
                    "استخدم العربية والمصطلحات الإنجليزية بين قوسين فقط. "
                    "اجعل الرد كاملاً وغير مقتطع."
                )
                reply_text = self._generate_ai(prompt, tweet.text)
                
                if reply_text:
                    final_reply = reply_text[:275] if len(reply_text) > 280 else reply_text
                    self.x_client.create_tweet(text=final_reply, in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO news VALUES (?, ?, ?)", (f"rep_{tweet.id}", "reply", datetime.now().isoformat()))
                    conn.commit()
                conn.close()
                time.sleep(5)
        except Exception as e: logging.error(f"Reply Error: {e}")

    def run_cycle(self):
        self.handle_smart_replies()
        ctype = random.choices(['news', 'poll', 'quiz'], weights=[70, 15, 15])[0]
        
        if ctype == 'news':
            self.post_tech_news()
        elif ctype == 'poll':
            self.post_interactive("صغ استطلاع رأي تقني حماسي بلهجة سعودية عن مقارنة منتجات. خيارات قصيرة.")
        else:
            self.post_interactive("صغ مسابقة تقنية للأذكياء بلهجة سعودية حماسية عن معلومة غريبة.")

    def post_tech_news(self):
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/", "https://techcrunch.com/feed/"]
        random.shuffle(sources)
        for url in sources:
            feed = feedparser.parse(url)
            for e in feed.entries[:10]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    if any(w in e.title.lower() for w in ["apple", "nvidia", "ai", "tesla", "leak", "openai", "m4", "ios"]):
                        prompt = (
                            "أنت صانع محتوى تقني سعودي. صغ الخبر كثريد حماسي بلهجة بيضاء. "
                            "اللغة: العربية والمصطلحات الإنجليزية بين قوسين فقط. "
                            "الهيكلية: 1. Hook خاطف. 2. تحليل تطبيقي. 3. مثال واقعي. 4. سؤال تفاعلي."
                        )
                        content = self._generate_ai(prompt, f"الخبر: {e.title}\n{e.description}")
                        if content and self.post_thread(content, e.link):
                            conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                            conn.commit(); conn.close(); return
                conn.close()

    def post_interactive(self, prompt_instr):
        content = self._generate_ai(prompt_instr + " (باللغة العربية، لهجة بيضاء، مصطلحات بين قوسين)", "تفاعل")
        if content:
            safe_text = content[:270] + "\n#تقنية"
            self.x_client.create_tweet(text=safe_text)

    def _generate_ai(self, prompt, context):
        try:
            # تصحيح اسم النموذج لـ Gemini
            res = self.gemini_client.models.generate_content(model='models/gemini-1.5-flash', contents=f"{prompt}\n\nالسياق: {context}")
            return res.text
        except Exception as e:
            logging.error(f"Gemini Error: {e}. Switching to Backup...")
            res = self.ai_qwen.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role":"user","content":f"{prompt}\n\nالسياق: {context}"}])
            return res.choices[0].message.content

    def post_thread(self, content, url):
        tweets = [t.strip() for t in re.split(r'\n\s*\d+[\/\.\)]\s*|\n\n', content.strip()) if len(t.strip()) > 10]
        last_id = None
        for i, tweet in enumerate(tweets[:3]):
            text = tweet
            if i == len(tweets[:3]) - 1: text += f"\n\n🔗 المصدر: {url}\n#تقنية"
            if len(text) > 280: text = text[:277].rsplit(' ', 1)[0] + "..."
            try:
                res = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=last_id)
                last_id = res.data['id']
                time.sleep(6)
            except: break
        return True

if __name__ == "__main__":
    TechEliteBot().run_cycle()
