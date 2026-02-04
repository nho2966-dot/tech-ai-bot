import os, sqlite3, logging, hashlib, time, re, random
import tweepy, feedparser
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_FILE = "news.db"

# البرومبت الصارم: وظيفة الموديل هي التقييم قبل الصياغة
STRICT_AUTHORITY_PROMPT = """
أنت مدقق محتوى تقني في (TechElite). مهمتك الحالية هي تصفية الأخبار ونشر المفيد منها فقط.

القواعد الصارمة:
1. الجودة: إذا كان الخبر مبهمًا، تافهًا، أو مجرد إشاعة ضعيفة، لا تصغِ شيئًا واكتب فقط: [REJECTED].
2. المصداقية: التزم بالحقائق التقنية المذكورة في النص حصراً.
3. التنسيق (في حال القبول):
[TWEET_1]: حقيقة تقنية مركزية واضحة ومباشرة (بدون غموض).
[TWEET_2]: تفاصيل تقنية (Technical Details) مع ذكر المصطلحات الإنجليزية بين قوسين (Term).
[TWEET_3]: الأثر العملي لهذا الخبر على المستخدم أو السوق.

ممنوع استخدام عبارات تسويقية أو كلمات مبهمة مثل "قريبًا" أو "ربما" مالم تكن جزءًا من حقيقة تقنية مؤكدة.
"""

class TechEliteAuthority:
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
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def _is_valuable_content(self, title):
        """فلتر الكلمات المفتاحية لمنع الأخبار غير المفيدة قبل إرسالها للذكاء الاصطناعي"""
        useless_keywords = ['deal', 'discount', 'sale', 'giveaway', 'rumor', 'maybe', 'opinion']
        return not any(word in title.lower() for word in useless_keywords)

    def _generate_ai(self, prompt, context):
        try:
            r = self.ai_client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role":"system","content":prompt},{"role":"user","content":context}],
                temperature=0.0 # أدنى درجة حرارة لضمان المنطق المطلق والصفر هلوسة
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}"); return None

    def _smart_parse(self, text):
        if "[REJECTED]" in text or len(text) < 50:
            return []
        
        tweets = []
        segments = re.split(r'\[TWEET_\d+\]', text)
        for seg in segments:
            clean_seg = seg.strip()
            if clean_seg and len(clean_seg) > 15:
                tweets.append(clean_seg)
        return tweets[:3]

    def post_thread(self, ai_text, url):
        tweets = self._smart_parse(ai_text)
        if not tweets:
            logging.info("🚫 تم استبعاد المحتوى لعدم كفاية الجودة أو الوضوح.")
            return False

        footer = f"🔗 المصدر الموثوق:\n{url}\n\n🛡️ TechElite | رصد دقيق"
        tweets.append(footer)

        last_id = None
        for i, t in enumerate(tweets):
            try:
                prefix = f"{i+1}/ " if i < len(tweets)-1 else ""
                res = self.x_client.create_tweet(text=f"{prefix}{t}"[:278], in_reply_to_tweet_id=last_id)
                last_id = res.data["id"]
                time.sleep(15)
            except Exception as e:
                logging.error(f"Tweet Error: {e}"); break
        return True

    def run_cycle(self):
        published = 0
        sources = ["https://www.theverge.com/rss/index.xml", "https://9to5mac.com/feed/", "https://techcrunch.com/feed/"]
        random.shuffle(sources)

        for url in sources:
            if published >= 2: break
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                if published >= 2: break
                
                # طبقة الفلترة الأولى: الكلمات المفتاحية
                if not self._is_valuable_content(e.title): continue

                h = hashlib.sha256(e.title.encode()).hexdigest()
                conn = sqlite3.connect(DB_FILE)
                if not conn.execute("SELECT 1 FROM news WHERE hash=?", (h,)).fetchone():
                    # إرسال المحتوى الكامل للتقييم الصارم
                    context = f"Title: {e.title}\nFull Text: {getattr(e, 'summary', '')}"
                    ai_text = self._generate_ai(STRICT_AUTHORITY_PROMPT, context)
                    
                    if ai_text and self.post_thread(ai_text, e.link):
                        conn.execute("INSERT INTO news VALUES (?, ?, ?)", (h, e.title, datetime.now().isoformat()))
                        conn.commit(); published += 1
                        time.sleep(120) # فاصل زمني طويل بين الأخبار لتعزيز الرصانة
                conn.close()

if __name__ == "__main__":
    TechEliteAuthority().run_cycle()
