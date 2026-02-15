import os, sqlite3, hashlib, time, random, re, logging
from datetime import datetime
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

load_dotenv()

# --- إعدادات القمة 2026: تكلفة صفرية + تفاعل أقصى + إثارة عالية ---
CONFIG = {
    "DB": "sovereign_v550.db",
    "DAILY_MAX_TWEETS": 12,
    "REPLY_DELAY": 45,
    "MODELS": [
        {"name": "Groq-Free", "type": "openai", "base": "https://api.groq.com/openai/v1", "key": os.getenv("GROQ_API_KEY"), "model": "llama-3.3-70b-versatile"},
        {"name": "Gemini-Flash", "type": "google", "key": os.getenv("GOOGLE_API_KEY"), "model": "gemini-1.5-flash"},
        {"name": "OR-Free", "type": "openai", "base": "https://openrouter.ai/api/v1", "key": os.getenv("OPENROUTER_API_KEY"), "model": "google/gemini-2.0-flash-exp:free"},
        {"name": "Grok-Brain", "type": "openai", "base": "https://api.x.ai/v1", "key": os.getenv("XAI_API_KEY"), "model": "grok-4-1-fast-reasoning"}
    ]
}

RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SovereignPeak2026")

class SovereignBot:
    def __init__(self):
        self._init_db()
        self.sources = [
            "https://www.jook.me/rss/technology",
            "https://www.arabnews.com/rss/technology",
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://feeds.feedburner.com/Techmeme"
        ]
        
        if os.getenv("GOOGLE_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            me = self.x.get_me()
            self.bot_id = str(me.data.id) if me and me.data else None
            logger.info(f"المعرف السيادي النشط: {self.bot_id}")
        except Exception as e:
            logger.critical(f"خطأ في الاتصال بمنصة X: {e}")
            exit(1)

    def _init_db(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()

    def _brain(self, content="", mode="POST"):
        sys_rules = (
            "أنت مستشار تقني نخبوي خليجي. "
            "ابدأ بجملة صادمة أو صورة ذهنية قوية، اربطها مباشرة بالسيادة الرقمية للفرد (HUMAIN OS)، "
            "كن فلسفياً، عميقاً، مثيراً للنقاش، لغة وقورة لكن مشوقة. أقل من 240 حرف."
        )
        prompts = {
            "POST": f"حلل بأسلوب 'جوك' الصادم والمثير: {content}",
            "REPLY": f"رد فلسفي وقور ومثير للنقاش العميق: {content}",
            "TOOL_POST": f"اقترح أداة ذكاء اصطناعي ثورية في 2026: {content}. قدم وصفاً صادماً، خطوتين فقط للاستفادة في سيادة الفرد، ثم سؤال استفزازي قوي."
        }

        for m in CONFIG["MODELS"]:
            if not m.get("key"): continue
            try:
                text = ""
                if m["type"] == "openai":
                    client = OpenAI(api_key=m["key"], base_url=m["base"])
                    res = client.chat.completions.create(
                        model=m["model"],
                        messages=[{"role": "system", "content": sys_rules}, {"role": "user", "content": prompts.get(mode, prompts["POST"])}],
                        temperature=0.6,
                        max_tokens=190,
                        timeout=35
                    )
                    text = res.choices[0].message.content.strip()
                
                elif m["type"] == "google":
                    model = genai.GenerativeModel(m["model"])
                    res = model.generate_content(
                        f"{sys_rules}\n\n{prompts.get(mode, prompts['POST'])}",
                        generation_config=genai.types.GenerationConfig(temperature=0.6, max_output_tokens=190)
                    )
                    text = res.text.strip()

                text = re.sub(r'<(thinking|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
                text = text[:235]  # مساحة للهاشتاجات
                
                tags = " #سيادة_رقمية #HUMAIN_OS #AI2026"
                full_text = f"{RTL_EMBED}{RTL_MARK}{text}{tags}{RTL_POP}"
                
                logger.info(f"تم التوليد عبر {m['name']} ({len(full_text)} حرف)")
                return full_text
            
            except Exception as e:
                logger.warning(f"المحرك {m['name']} فشل: {str(e)[:100]}...")
                continue
        
        fallback = f"{RTL_EMBED}{RTL_MARK}في عصر الخوارزميات، الوعي هو السلاح الوحيد الذي لا يُخترق.{RTL_POP}"
        return fallback

    def fetch(self):
        headers = {'User-Agent': 'SovereignPeak/2026.02'}
        for src in self.sources:
            try:
                resp = requests.get(src, headers=headers, timeout=15)
                feed = feedparser.parse(resp.content)
                count = 6 if any(d in src for d in ["techcrunch", "theverge"]) else 4
                for e in feed.entries[:count]:
                    title = (e.title or "").strip()
                    if not title: continue
                    h = hashlib.sha256(title.encode()).hexdigest()
                    with sqlite3.connect(CONFIG["DB"]) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title) VALUES (?,?)", (h, title))
                        c.commit()
            except Exception as e:
                logger.error(f"فشل جلب {src}: {e}")

    def handle_interactions(self):
        last_id = self._get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id, max_results=5)
            if not mentions.data: return
            
            new_last_id = last_id
            for m in mentions.data:
                new_last_id = max(new_last_id, str(m.id))
                with sqlite3.connect(CONFIG["DB"]) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(m.id),)).fetchone():
                        continue
                    reply = self._brain(m.text, mode="REPLY")
                    if reply and len(reply) <= 280:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=m.id)
                        c.execute("INSERT INTO replies VALUES (?,?)", (str(m.id), datetime.now().isoformat()))
                        c.commit()
                        time.sleep(CONFIG["REPLY_DELAY"])
            
            self._update_meta("last_mention_id", new_last_id)
        except Exception as e:
            logger.warning(f"مشكلة في المنشنز: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))
        if count >= CONFIG["DAILY_MAX_TWEETS"]:
            return
        
        try:
            content = None
            row_h = None
            
            with sqlite3.connect(CONFIG["DB"]) as c:
                # 35% فرصة لمنشور أدوات AI
                if random.random() < 0.35:
                    topic = random.choice(["إنتاجية", "خصوصية", "أتمتة", "إبداع", "سيادة رقمية"])
                    content = self._brain(f"أفضل أداة في {topic} 2026", "TOOL_POST")
                else:
                    row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
                    if row:
                        content = self._brain(row[1], "POST")
                        row_h = row[0]
            
            if content and len(content) <= 280:
                # 30% فرصة لاستطلاع رأي
                if random.random() < 0.30:
                    poll = {
                        "options": ["اتفق بشدة", "أحتاج تفكير", "أرفض تماماً"],
                        "duration_minutes": 1440
                    }
                    tweet = self.x.create_tweet(text=content, poll=poll)
                else:
                    tweet = self.x.create_tweet(text=content)
                
                logger.info(f"تم النشر: {tweet.data['id']} | طول: {len(content)}")
                
                if row_h:
                    c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row_h,))
                c.commit()
                self._update_meta(f"daily_count_{today}", str(count + 1))
                
                time.sleep(random.uniform(60, 240))  # تأخير طبيعي أكبر
            else:
                logger.warning("محتوى فارغ أو طويل جداً")
                
        except Exception as e:
            logger.warning(f"خطأ في dispatch: {e}")

    def _get_meta(self, key, default="0"):
        with sqlite3.connect(CONFIG["DB"]) as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key, value):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            c.commit()

    def run(self):
        self.fetch()
        self.handle_interactions()
        self.dispatch()

if __name__ == "__main__":
    SovereignBot().run()
