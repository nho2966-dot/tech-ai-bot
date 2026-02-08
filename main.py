import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class ZenithGlobalAgent:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        # مصادر العمالقة الموثوقة عالمياً
        self.sources = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://wired.com/feed/rss",
            "https://arstechnica.com/feed/",
            "https://9to5mac.com/feed/",
            "https://9to5google.com/feed/"
        ]
        self.charter = (
            "أنت المهندس التقني والمستشار الاستراتيجي الأعلى. فكرك نخبوي.\n"
            "1. الهوية: خليجية نُخبوية رصينة، مصطلحات تقنية دقيقة بين قوسين ().\n"
            "2. المنطق: (تحليل الخبر + المقارنة التنافسية + الأثر على السيادة الرقمية والخصوصية).\n"
            "3. الفلاتر: منع الهلوسة، منع الأخبار البائتة (>36س)، منع الرد على النفس أو التكرار."
        )

    def _init_db(self):
        with sqlite3.connect("zenith_v71.db") as conn:
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
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": self.charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.1
            ).choices[0].message.content.strip()
            if re.match(r'^[ \u0600-\u06FF0-9a-zA-Z()\[\]\.\!\?\-\n\r]+$', res):
                return res
            return ""
        except: return ""

    def _is_locked(self, task, minutes):
        with sqlite3.connect("zenith_v71.db") as conn:
            row = conn.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            if row and datetime.now() < datetime.fromisoformat(row[0]) + timedelta(minutes=minutes):
                return True
        return False

    def handle_mentions(self):
        if self._is_locked("mentions", 20): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id)
            if not mentions.data: return
            with sqlite3.connect("zenith_v71.db") as conn:
                for t in mentions.data:
                    h = hashlib.sha256(f"{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue
                    reply = self._strategic_brain(f"حلل ورد بذكاء خليجي نُخبوي مقتضب: {t.text}")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        conn.commit()
                        time.sleep(random.randint(60, 120))
                conn.execute("INSERT OR REPLACE INTO throttle VALUES ('mentions', ?)", (datetime.now().isoformat(),))
        except Exception as e: logging.warning(f"Shield: {e}")

    def post_global_scoops(self):
        """سحب الأخبار من المصادر العالمية وتحويلها لثريدات استراتيجية"""
        if self._is_locked("news", 120): return # فحص الأخبار كل ساعتين

        for url in self.sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                p_date = datetime(*entry.published_parsed[:6])
                # فلتر الـ 36 ساعة الصارم
                if (datetime.now() - p_date) > timedelta(hours=36): continue

                h = hashlib.sha256(entry.title.encode()).hexdigest()
                with sqlite3.connect("zenith_v71.db") as conn:
                    if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    
                    instr = "صغ ثريداً استراتيجياً (Hook-Value-Impact-CTA). قارن بمنافسين ووضح أثر التقنية على الفرد والخصوصية."
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
                        return # نكتفي بخبر واحد نخبوي في كل دورة لضمان المعدل

if __name__ == "__main__":
    bot = ZenithGlobalAgent()
    bot.handle_mentions()
    bot.post_global_scoops()
