import os, sqlite3, logging, hashlib, time, random
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignEliteIronBotV88:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        
        # حصر المصادر في "القوة التقنية" فقط ومنع المصادر العامة
        self.elite_sources = [
            "https://www.bloomberg.com/technology/rss",
            "https://wccftech.com/feed/",
            "https://9to5mac.com/feed/",
            "https://www.digitimes.com/rss/daily.xml",
            "https://www.macrumors.com/macrumors.xml"
        ]

    def _init_db(self):
        with sqlite3.connect("sovereign_memory.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memory (h PRIMARY KEY, type TEXT, dt TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS throttle (task TEXT PRIMARY KEY, last_run TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _strategic_brain(self, prompt, context=""):
        """محرك السيادة اللغوية: خليجية بيضاء، تقنية بحتة، صفر إنشائية"""
        try:
            charter = (
                "أنت خبير تقني خليجي نُخبوي. لغتك (خليجية بيضاء) رصينة ومختصرة جداً.\n"
                "1. تخصصك: هاردوير، أدوات AI، تسريبات أجهزة فقط. ممنوع أي مواضيع أخرى (حلويات، هدايا، عام).\n"
                "2. المنهج: ادخل في صلب الموضوع (السكوب) مباشرة. لا مقدمات (في عالم، يسعدنا).\n"
                "3. الهيكل: عنوان مثير -> مقدمة سكوب -> أبرز الميزات (نقاط) -> تفاصيل تقنية (specs) -> سعر وتوفر -> سؤال.\n"
                "4. اللغة: الإنجليزي بين أقواس (). لا تستخدم لغة مدرسية."
            )
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.0 # صرامة مطلقة في دقة المعلومات
            ).choices[0].message.content.strip()
            return res
        except: return ""

    def post_elite_scoop(self):
        """نشر السكوبات: فلترة استراتيجية ضد المحتوى الهزيل"""
        logging.info("📡 Scanning for elite technical scoops...")
        all_entries = []
        for url in self.elite_sources:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                try:
                    p_date = datetime(*e.published_parsed[:6])
                    if (datetime.now() - p_date) <= timedelta(hours=24):
                        # فلتر الكلمات الممنوعة (لضمان التقنية فقط)
                        forbidden = ["candy", "gift", "valentine", "fashion", "lifestyle"]
                        if any(word in e.title.lower() or word in e.description.lower() for word in forbidden):
                            continue
                        all_entries.append(e)
                except: continue

        if not all_entries: return
        random.shuffle(all_entries)

        for entry in all_entries:
            h = hashlib.sha256(entry.title.encode()).hexdigest()
            with sqlite3.connect("sovereign_memory.db") as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                
                prompt = "صغ سكوب تقني نُخبوي خليجي (Technical Scoop) عن هذا الخبر مع المواصفات الكاملة."
                content = self._strategic_brain(prompt, f"{entry.title}\n{entry.description}")
                
                # شرط القيمة المضافة: يجب أن يحتوي على تفاصيل تقنية دسمة
                if content and len(content) > 150 and any(kw in content for kw in ["(", ")", "معالج", "سعر", "تقنية"]):
                    try:
                        self.x.create_tweet(text=content)
                        conn.execute("INSERT OR IGNORE INTO memory VALUES (?,?,?)", (h, "SCOOP", datetime.now().isoformat()))
                        conn.commit()
                        logging.info("🎯 Elite Technical Scoop Published.")
                        return 
                    except: pass

if __name__ == "__main__":
    bot = SovereignEliteIronBotV88()
    bot.post_elite_scoop()
