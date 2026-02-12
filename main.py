import os, sqlite3, hashlib, json, time, random, re
import numpy as np
from datetime import datetime
import tweepy, feedparser, requests
from dotenv import load_dotenv
from openai import OpenAI
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

# --- 1. الإعدادات النهائية المستقرة لعام 2026 ---
CONFIG = {
    "DB": "sovereign_v550.db",
    "COOLDOWN_MINUTES": 75,
    "SIM_THRESHOLD": 0.88,
    "PEAK_HOURS": [8,9,10,11,12,13,17,18,19,20,21,22],
    "POLL_CHANCE": 0.40,
    "QUIZ_CHANCE": 0.20,
    "MAX_REPLIES": 8,
    "DAILY_MAX_TWEETS": 14,
    "REPLY_DELAY_MIN": 12,
    "REPLY_DELAY_MAX": 35
}

RTL_EMBED, RTL_MARK, RTL_POP = '\u202b', '\u200f', '\u202c'

# سجلات تفصيلية للمراقبة الاحترافية (تشمل اسم الدالة ورقم السطر)
logger = logging.getLogger("SovereignBot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("sovereign_v550.log", maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s | %(funcName)s:%(lineno)d')
handler.setFormatter(formatter)
logger.addHandler(handler)

class SovereignControversyV550:
    def __init__(self):
        self.embedding_dim = 1536
        self._init_db()

        try:
            self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True
            )
            me = self.x.get_me()
            self.bot_id = str(me.data.id) if me and me.data else None
            if not self.bot_id: raise Exception("Auth Failed")
            logger.info(f"تم تفعيل وكيل السيادة الرقمية - المعرف: @ID: {self.bot_id}")
        except Exception as e:
            logger.critical(f"فشل تهيئة الأنظمة الأساسية: {e}"); raise SystemExit(1)

        # المصادر العربية والعالمية لتعزيز ظهور HUMAIN و G42 و Falcon
        self.sources = [
            "https://www.arabnews.com/rss/technology",
            "https://www.zawya.com/en/rss/technology",
            "https://www.alkhaleej.ae/rss/technology",
            "https://www.emaratalyoum.com/rss/technology",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://hackernoon.com/feed/tag/ai"
        ]

    def _init_db(self):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, embedding TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, h TEXT UNIQUE, title TEXT, score REAL, status TEXT DEFAULT 'PENDING', created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, user_id TEXT, created_at TEXT)")
            c.commit()

    def _get_or_init_meta(self, key, default):
        with sqlite3.connect(CONFIG["DB"]) as c:
            row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def _update_meta(self, key, value):
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, str(value)))
            c.commit()

    def _check_daily_limit(self):
        today = datetime.now().date().isoformat()
        key = f"daily_count_{today}"
        count = int(self._get_or_init_meta(key, "0"))
        if count >= CONFIG["DAILY_MAX_TWEETS"]:
            logger.warning(f"الحد اليومي مكتمل ({count}/{CONFIG['DAILY_MAX_TWEETS']})")
            return False
        self._update_meta(key, str(count + 1))
        return True

    def _cleanup_old_daily_counts(self):
        today = datetime.now().date().isoformat()
        with sqlite3.connect(CONFIG["DB"]) as c:
            c.execute("DELETE FROM meta WHERE key LIKE 'daily_count_%' AND key < ?", (f"daily_count_{today}",))
            c.commit()
            logger.info("تم تنظيف عدادات الأيام السابقة.")

    def _embedding(self, text):
        try:
            res = self.ai.embeddings.create(model="text-embedding-3-small", input=text)
            return np.array(res.data[0].embedding)
        except: return np.zeros(self.embedding_dim)

    def _cosine(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _is_semantic_duplicate(self, emb):
        with sqlite3.connect(CONFIG["DB"]) as c:
            rows = c.execute("SELECT embedding FROM memory").fetchall()
        for r in rows:
            old_emb = np.array(json.loads(r[0]))
            if self._cosine(emb, old_emb) > CONFIG["SIM_THRESHOLD"]: return True
        return False

    def _safe_text(self, text):
        text = text.strip()
        return text[:275] + "…" if len(text) > 280 else text

    def _brain(self, content, mode="POST"):
        system_rules = (
            "أنت مستشار تقني خليجي رصين. لغتك خليجية بيضاء مباشرة ومثيرة للجدل الذكي. "
            "التركيز: (HUMAIN OS)، (الوكلاء الشخصيين)، (السيادة الرقمية)، (المعالجة المحلية). "
            "في POLL: سطر 1 السؤال، الأسطر التالية خيارات (أقصى 24 حرف). "
            "لا تضيف أي معلومات افتراضية أو هلوسة. التزم بالواقع التقني حتى فبراير 2026 فقط. "
            "أنهِ دائماً بسؤال تفاعلي للمتابعين."
        )
        prompts = {
            "POST": f"حلل هذا الخبر للفرد بأسلوب نخبوي وجدلي: {content}",
            "REPLY": f"رد خليجي محترف يثير الجدل حول تمكين الفرد وأنهِ بسؤال: {content}",
            "QUIZ": "سؤال ذكي واحد عن بناء الوكلاء الشخصيين أو سيادة البيانات.",
            "POLL": "استطلاع رأي يثير ضجة حول وكلاء الذكاء الاصطناعي (Agentic AI). السؤال سطر والخيارات في أسطر منفصلة."
        }
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompts[mode]}],
                timeout=40
            )
            return f"{RTL_EMBED}{RTL_MARK}{res.choices[0].message.content.strip()}{RTL_POP}"
        except: return ""

    def fetch(self):
        for src in self.sources:
            try:
                feed = feedparser.parse(src)
                for e in feed.entries[:10]:
                    title = e.title.strip()
                    blacklist = ["stock", "revenue", "quarterly", "acquisition", "ceo", "shares"]
                    if any(x in title.lower() for x in blacklist): continue

                    # رفع وزن HUMAIN OS لضمان الصدارة
                    targets = {
                        "humain os": 4.8, "humain one": 4.8, "وكيل ذكي": 4.2,
                        "سيادة رقمية": 4.2, "sovereign ai": 4.0, "خصوصية": 3.8, "agentic": 3.9
                    }

                    score = 4.0
                    t_lower = title.lower()
                    matched = False
                    for k, v in targets.items():
                        if k in t_lower:
                            score *= v; matched = True; break
                    
                    if not matched: continue

                    h = hashlib.sha256(title.encode()).hexdigest()
                    emb = self._embedding(title)
                    if self._is_semantic_duplicate(emb): continue

                    with sqlite3.connect(CONFIG["DB"]) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title, score, created_at) VALUES (?,?,?,?)", (h, title, score, datetime.now().isoformat()))
                        c.execute("INSERT OR IGNORE INTO memory (h, embedding) VALUES (?,?)", (h, json.dumps(emb.tolist())))
                        c.commit()
            except: continue

    def handle_interactions(self):
        if not self.bot_id: return
        last_mention_id = self._get_or_init_meta("last_mention_id", "0")

        try:
            mentions = self.x.get_users_mentions(
                id=self.bot_id,
                since_id=int(last_mention_id) if last_mention_id != "0" else None,
                max_results=15
            )

            if not mentions or not mentions.data: return

            new_last_id = int(last_mention_id)
            with sqlite3.connect(CONFIG["DB"]) as c:
                for m in mentions.data:
                    tweet_id_str = str(m.id)
                    new_last_id = max(new_last_id, m.id)

                    if c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (tweet_id_str,)).fetchone():
                        continue
                    
                    reply_text = self._brain(m.text, mode="REPLY")
                    if reply_text:
                        try:
                            self.x.create_tweet(text=self._safe_text(reply_text), in_reply_to_tweet_id=tweet_id_str)
                            c.execute("INSERT INTO replies VALUES (?,?,?)", (tweet_id_str, str(m.author_id), datetime.now().isoformat()))
                            c.commit()
                            logger.info(f"تم الرد على منشن: {tweet_id_str}")
                            time.sleep(random.uniform(CONFIG["REPLY_DELAY_MIN"], CONFIG["REPLY_DELAY_MAX"]))
                        except tweepy.TooManyRequests:
                            time.sleep(900); break

            self._update_meta("last_mention_id", str(new_last_id))
        except Exception as e: logger.error(f"خطأ معالجة المنشنز: {e}")

    def dispatch(self):
        now = datetime.now()
        if now.hour not in CONFIG["PEAK_HOURS"]: return
        if not self._check_daily_limit(): return
        
        with sqlite3.connect(CONFIG["DB"]) as c:
            last = c.execute("SELECT value FROM meta WHERE key='last_publish'").fetchone()
            if last and (now - datetime.fromisoformat(last[0])).total_seconds() / 60 < CONFIG["COOLDOWN_MINUTES"]: return

            rand = random.random()
            try:
                if rand < CONFIG["QUIZ_CHANCE"]:
                    text = self._brain("", mode="QUIZ")
                    if text: 
                        self.x.create_tweet(text=self._safe_text(text))
                        logger.info(f"نُشرت مسابقة: {text[:60]}")
                elif rand < (CONFIG["QUIZ_CHANCE"] + CONFIG["POLL_CHANCE"]):
                    raw = self._brain("", mode="POLL")
                    lines = [l.strip() for l in raw.split('\n') if l.strip()]
                    poll_text = self._safe_text(lines[0] if lines else "مستقبل السيادة الرقمية؟")
                    
                    options = []
                    seen = set()
                    for line in lines[1:6]:
                        cleaned = re.sub(r'^\s*[\d•\-\*\+]\.?\s*', '', line.strip())[:24].strip()
                        if cleaned and len(cleaned) >= 3 and cleaned not in seen:
                            options.append(cleaned); seen.add(cleaned)
                        if len(options) == 4: break
                    
                    if len(options) < 2:
                        options = ["سيادة محلية 100%", "سحابة قوية مراقبة", "لا أثق بالوكلاء", "أحتاج تجربة أطول"]
                    
                    self.x.create_tweet(text=poll_text, poll_options=options[:4], poll_duration_minutes=1440)
                    logger.info(f"نُشر استطلاع: {poll_text[:60]}")
                else:
                    row = c.execute("SELECT id, title FROM queue WHERE status='PENDING' ORDER BY score DESC LIMIT 1").fetchone()
                    if row:
                        content = self._brain(row[1], mode="POST")
                        if content:
                            self.x.create_tweet(text=self._safe_text(content))
                            c.execute("UPDATE queue SET status='PUBLISHED' WHERE id=?", (row[0],))
                            logger.info(f"نُشر سكوب: {row[1][:60]}")
                
                self._update_meta("last_publish", now.isoformat())
                today_key = f"daily_count_{now.date().isoformat()}"
                logger.info(f"العداد اليومي: {self._get_or_init_meta(today_key, '0')}/{CONFIG['DAILY_MAX_TWEETS']}")

            except Exception as e: logger.error(f"خطأ أثناء النشر: {e}")

    def run_forever(self):
        logger.info("بدء تشغيل دورة السيادة الرقمية 2026...")
        self._cleanup_old_daily_counts()
        while True:
            try:
                self.fetch()
                self.handle_interactions()
                self.dispatch()
                time.sleep(random.randint(600, 1200))
            except Exception as e:
                logger.error(f"خطأ في الحلقة الرئيسية: {e}"); time.sleep(300)

if __name__ == "__main__":
    SovereignControversyV550().run_forever()
