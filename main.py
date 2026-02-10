import os, sqlite3, logging, hashlib, random, time, re
from datetime import datetime, timedelta
import tweepy, feedparser, requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# === 1. Governance & Environmental Setup ===
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
DB_FILE = "sovereign_memory.db"

# محددات النخبة (لضمان جودة السكوبات)
BASE_ELITE_SCORE = {
    "leak": 3, "exclusive": 3, "hands-on": 2, "benchmark": 2,
    "specs": 2, "chip": 2, "tool": 2, "update": 1,
    "ai agent": 3, "gpu": 2, "new feature": 2
}

class SovereignApexBotV100:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://9to5google.com/feed/",
            "https://9to5mac.com/feed/",
            "https://www.macrumors.com/macrumors.xml",
            "https://venturebeat.com/feed/",
            "https://wccftech.com/feed/"
        ]

    # === 2. Database Intelligence (The Memory) ===
    def _init_db(self):
        with sqlite3.connect(DB_FILE) as c:
            # ذاكرة منع التكرار (Semantic Hash)
            c.execute("CREATE TABLE IF NOT EXISTS memory (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            # التحكم في وتيرة النشر (Throttle)
            c.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")
            # ذاكرة التعلم السياقي (Reinforcement Learning)
            c.execute("""CREATE TABLE IF NOT EXISTS context_memory (
                topic TEXT, hour INTEGER, style TEXT, strategy TEXT, reward REAL)""")
            # بروفايلات المستخدمين (Profiling)
            c.execute("CREATE TABLE IF NOT EXISTS user_profile (user_id TEXT PRIMARY KEY, level TEXT)")
            c.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    # === 3. Safety & Logic Guards ===
    def _is_throttled(self, task, minutes):
        with sqlite3.connect(DB_FILE) as c:
            r = c.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            return r and datetime.now() < datetime.fromisoformat(r[0]) + timedelta(minutes=minutes)

    def _lock(self, task):
        with sqlite3.connect(DB_FILE) as c:
            c.execute("INSERT OR REPLACE INTO throttle VALUES (?,?)", (task, datetime.now().isoformat()))
            c.commit()

    def _fetch_url_context(self, url):
        """Grounding Engine: استخراج بيانات الرابط لمنع الهلوسة"""
        try:
            r = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            return f"Title: {soup.title.text}\nContext: {soup.find('meta', {'name':'description'})['content']}"
        except: return ""

    # === 4. AI Strategic Brain ===
    def _brain(self, mission, context):
        charter = (
            "أنت محلل تقني خليجي نخبوي. اللغة: خليجية بيضاء رصينة.\n"
            "الشرط الحرج: التزم فقط بالحقائق المذكورة. لا تخمن أرقاماً أو تواريخ.\n"
            "التركيز: الفرد، الإنتاجية، السكوبات التقنية الصلبة."
        )
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                temperature=0.0,
                messages=[{"role":"system","content":charter}, {"role":"user","content":f"Context: {context}\nMission: {mission}"}]
            )
            return res.choices[0].message.content.strip()
        except: return ""

    # === 5. Learning & Reward System ===
    def _get_best_style(self, topic):
        """اختيار أفضل أسلوب بناءً على الـ ROI السابق لهذا الموضوع"""
        with sqlite3.connect(DB_FILE) as c:
            res = c.execute("SELECT style FROM context_memory WHERE topic=? ORDER BY reward DESC LIMIT 1", (topic,)).fetchone()
        return res[0] if res else random.choice(["Analytical", "Viral", "Story"])

    def _detect_topic(self, text):
        for topic, kws in {"AI": ["ai", "gpt", "llm"], "HARDWARE": ["chip", "gpu", "intel", "apple"], "CYBER": ["hack", "leak", "security"]}.items():
            if any(k in text.lower() for k in kws): return topic
        return "GENERAL"

    # === 6. Main Action Engines ===
    def post_elite_scoop(self):
        if self._is_throttled("post", 100): return
        
        candidates = []
        for src in self.sources:
            feed = feedparser.parse(src)
            for e in feed.entries[:5]:
                # فلترة الحداثة والنخبوية
                text = (e.title + e.description).lower()
                score = sum(v for k, v in BASE_ELITE_SCORE.items() if re.search(rf"\b{k}\b", text))
                if score >= 3 and len(e.description) > 100:
                    candidates.append(e)

        if not candidates: return
        target = random.choice(candidates)
        topic = self._detect_topic(target.title)
        
        # تفعيل الـ Reinforcement: الاستكشاف مقابل الاستثمار
        strategy = "EXPLORE" if random.random() < 0.2 else "EXPLOIT"
        style = self._get_best_style(topic) if strategy == "EXPLOIT" else random.choice(["Debate", "Future Speculation"])

        # إنشاء المحتوى
        h = hashlib.sha256((target.title + target.description[:100]).encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return

            content = self._brain(f"صغ سكوب بأسلوب {style} يركز على القيمة للفرد.", f"{target.title}\n{target.description}")
            if content:
                try:
                    self.x.create_tweet(text=content)
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.execute("INSERT INTO context_memory VALUES (?,?,?,?,?)", (topic, datetime.now().hour, style, strategy, 0.0))
                    c.commit()
                    self._lock("post")
                    logging.info(f"🚀 Published: {topic} | {style}")
                except Exception as e: logging.error(e)

    def handle_mentions(self):
        if self._is_throttled("mentions", 15): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, expansions=['author_id', 'entities'])
            if not mentions.data: return
            with sqlite3.connect(DB_FILE) as c:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    
                    # تحليل الروابط + Profiling
                    urls = t.entities.get('urls') if t.entities else None
                    context = self._fetch_url_context(urls[0]['expanded_url']) if urls else t.text
                    
                    reply = self._brain("رد تقني خليجي نخبوي ومختصر.", context)
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        c.commit()
        except: pass

if __name__ == "__main__":
    bot = SovereignApexBotV100()
    bot.handle_mentions()
    bot.post_elite_scoop()
