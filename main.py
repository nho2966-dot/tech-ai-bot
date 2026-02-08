import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

# إعداد الرقابة والتدقيق
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class OmniscientSovereignV75:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        
        # مصادر النخبة التقنية العالمية
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss",
            "https://arstechnica.com/feed/",
            "https://9to5mac.com/feed/",
            "https://9to5google.com/feed/"
        ]

        # ميثاق الوكيل الاستراتيجي (Zero-Hallucination Charter)
        self.charter = (
            "أنت المستشار التقني الأعلى وعقل مدبر في الثورة الصناعية الرابعة.\n"
            "1. الهوية: لغة خليجية نُخبوية رصينة، مصطلحات تقنية دقيقة بين قوسين ().\n"
            "2. المنطق: تحليل (الخبر + المقارنة التنافسية + الأثر على السيادة الرقمية والإنتاجية).\n"
            "3. الفلاتر: دقة 100%، منع الأخبار القديمة (>36س)، منع الرد على النفس أو تكرار الرد نهائياً."
        )

    def _init_db(self):
        with sqlite3.connect("sovereign_memory.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _strategic_brain(self, prompt, context=""):
        """محرك التفكير العاقل ومنع الهلوسة"""
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.1
            ).choices[0].message.content.strip()
            return res if re.match(r'^[ \u0600-\u06FF0-9a-zA-Z()\[\]\.\!\?\-\n\r]+$', res) else ""
        except Exception as e:
            logging.error(f"AI Brain Failure: {e}")
            return ""

    def _is_throttled(self, task, minutes):
        with sqlite3.connect("sovereign_memory.db") as conn:
            res = conn.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            if res and datetime.now() < datetime.fromisoformat(res[0]) + timedelta(minutes=minutes):
                return True
        return False

    def handle_mentions(self):
        """الردود الذكية: فلترة صارمة لمنع الرد على النفس أو تكرار الرد لنفس الشخص"""
        if self._is_throttled("mentions", 15): return
        logging.info("🔎 Checking mentions...")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id)
            if not mentions.data: return

            with sqlite3.connect("sovereign_memory.db") as conn:
                for t in mentions.data:
                    h = hashlib.sha256(f"{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue

                    reply = self._strategic_brain(f"رد بتحليل مقتضب ونخبوي: {t.text}")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        conn.commit()
                        time.sleep(random.randint(60, 120))
                conn.execute("INSERT OR REPLACE INTO throttle VALUES ('mentions', ?)", (datetime.now().isoformat(),))
        except Exception as e: logging.warning(f"Mentions Shield: {e}")

    def post_global_scoops(self):
        """نشر السكوبات: فلتر 36 ساعة + تحليل المقارنة"""
        if self._is_throttled("news", 120): return 
        logging.info("📡 Scanning global sources...")
        all_entries = []
        for url in self.sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                try:
                    p_date = datetime(*entry.published_parsed[:6])
                    if (datetime.now() - p_date) <= timedelta(hours=36):
                        all_entries.append(entry)
                except: continue

        if not all_entries: return
        entry = random.choice(all_entries)
        h = hashlib.sha256(entry.title.encode()).hexdigest()
        
        with sqlite3.connect("sovereign_memory.db") as conn:
            if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return
            
            instr = "صغ ثريداً استراتيجياً نخبويًا (Hook-Value-Impact-CTA). قارن بمنافسين."
            content = self._strategic_brain(instr, f"{entry.title}\n{entry.description}")
            
            if content:
                tweets = [t.strip() for t in content.split("---") if len(t.strip()) > 10]
                p_id = None
                for txt in tweets:
                    res = self.x.create_tweet(text=txt, in_reply_to_tweet_id=p_id)
                    p_id = res.data['id']
                    time.sleep(60)
                conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "THREAD", datetime.now().isoformat()))
                conn.execute("INSERT OR REPLACE INTO throttle VALUES ('news', ?)", (datetime.now().isoformat(),))
                conn.commit()
                logging.info(f"🎯 Scoop posted: {entry.title}")

    def engage_community(self):
        """وحدة التفاعل: مسابقات، استطلاعات، وأدوات AI عملية"""
        if self._is_throttled("engagement", 360): return 
        logging.info("🎨 Crafting engagement content...")
        
        prompt = random.choice([
            "صغ سؤالاً تقنياً عميقاً (Quiz) للمتابعين حول ممارسات الثورة الصناعية الرابعة.",
            "اشرح أداة (AI Tool) عملية تزيد إنتاجية الفرد بشكل ملموس بلهجة نُخبوية.",
            "اطرح تساؤلاً استراتيجياً للنقاش (Poll-style) حول مستقبل السيادة الرقمية."
        ])

        content = self._strategic_brain(prompt)
        if content:
            self.x.create_tweet(text=content)
            with sqlite3.connect("sovereign_memory.db") as conn:
                conn.execute("INSERT OR REPLACE INTO throttle VALUES ('engagement', ?)", (datetime.now().isoformat(),))
                conn.commit()
            logging.info("🔥 Engagement content published.")

if __name__ == "__main__":
    agent = OmniscientSovereignV75()
    agent.handle_mentions()
    agent.post_global_scoops()
    agent.engage_community()
