import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

# إعداد الرقابة الصارمة
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignIronBotV85:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.bot_id = self.x.get_me().data.id
        
        # شبكة الرادار العالمي (أباطرة الصحافة والسكوبات)
        self.elite_sources = [
            "https://www.bloomberg.com/technology/rss",
            "https://www.reuters.com/technology/rss",
            "https://9to5mac.com/feed/",
            "https://wccftech.com/feed/",
            "https://www.wired.com/feed/rss",
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/",
            "https://9to5google.com/feed/",
            "https://www.macrumors.com/macrumors.xml",
            "https://venturebeat.com/feed/",
            "https://arstechnica.com/feed/",
            "https://www.digitimes.com/rss/daily.xml"
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
        """محرك التفكير: صياغة خليجية نُخبوية + منع الهلوسة"""
        try:
            charter = (
                "أنت مستشار تقني خليجي نُخبوي. لغتك هي (العربية الخليجية البيضاء) الرصينة.\n"
                "الاشتراطات الصارمة:\n"
                "1. ممنوع الهلوسة: التزم بالأرقام والمواصفات الواردة في الخبر فقط.\n"
                "2. الهوية: ادخل في صلب الموضوع مباشرة (بيجي، بيعتمد، بيتكلمون عن، الهدف هو).\n"
                "3. التنسيق: اتبع هيكل (السكوب الصحفي) بنقاط واضحة وتفاصيل تقنية (Technical Specs).\n"
                "4. اللغة: المصطلحات الإنجليزية بين قوسين () دائماً.\n"
                "5. القيمة: إذا لم يحتوي الخبر على أرقام أو مواصفات تقنية جديدة، ارفض الصياغة فوراً."
            )
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": charter}, 
                          {"role": "user", "content": f"Context: {context}\nMission: {prompt}"}],
                temperature=0.1 # أقل درجة لضمان الدقة ومنع الإبداع الزائد (الهلوسة)
            ).choices[0].message.content.strip()
            return res
        except: return ""

    def _is_throttled(self, task, minutes):
        with sqlite3.connect("sovereign_memory.db") as conn:
            res = conn.execute("SELECT last_run FROM throttle WHERE task=?", (task,)).fetchone()
            if res and datetime.now() < datetime.fromisoformat(res[0]) + timedelta(minutes=minutes):
                return True
        return False

    def post_elite_scoop(self):
        """نشر السكوبات: حداثة (24س) + قيمة مضافة + تنسيق احترافي"""
        if self._is_throttled("main_scoop", 110): return
        
        logging.info("📡 Scanning global radar for fresh scoops...")
        all_entries = []
        for url in self.elite_sources:
            feed = feedparser.parse(url)
            for e in feed.entries[:3]:
                try:
                    p_date = datetime(*e.published_parsed[:6])
                    if (datetime.now() - p_date) <= timedelta(hours=24):
                        all_entries.append(e)
                except: continue

        if not all_entries: return
        # ترتيب الأخبار حسب الأحدث
        random.shuffle(all_entries)
        
        for entry in all_entries:
            h = hashlib.sha256(entry.title.encode()).hexdigest()
            with sqlite3.connect("sovereign_memory.db") as conn:
                if conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                
                prompt = (
                    "صغ 'سكوب صحفي' نُخبوي عن هذا الخبر بالصياغة الخليجية المعتمدة.\n"
                    "التزم بالهيكل: [عنوان مثير!] -> [مقدمة السكوب] -> [أبرز الميزات] -> [التفاصيل التقنية: معالج، شاشة، سعر، إلخ] -> [موعد الإطلاق] -> [سؤال تفاعلي]."
                )
                
                content = self._strategic_brain(prompt, f"{entry.title}\n{entry.description}")
                
                # شرط القيمة المضافة: يجب أن تكون التغريدة دسمة تقنياً
                if content and len(content) > 150 and "ارفض" not in content:
                    self.x.create_tweet(text=content)
                    conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "SCOOP", datetime.now().isoformat()))
                    conn.execute("INSERT OR REPLACE INTO throttle VALUES ('main_scoop', ?)", (datetime.now().isoformat(),))
                    conn.commit()
                    logging.info(f"🎯 Scoop Published: {entry.title[:30]}")
                    return # نشر خبر واحد عالي الجودة في كل دورة

    def handle_mentions(self):
        """الردود الذكية: صرامة في منع التكرار والرد على النفس"""
        if self._is_throttled("mentions", 20): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, max_results=5)
            if not mentions.data: return
            
            with sqlite3.connect("sovereign_memory.db") as conn:
                for t in mentions.data:
                    h = hashlib.sha256(f"rep_{t.id}".encode()).hexdigest()
                    if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone():
                        continue
                    
                    reply = self._strategic_brain(f"رد بتحليل تقني نخبوي ومختصر: {t.text}")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                        conn.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        conn.commit()
                        time.sleep(120)
            
            with sqlite3.connect("sovereign_memory.db") as conn:
                conn.execute("INSERT OR REPLACE INTO throttle VALUES ('mentions', ?)", (datetime.now().isoformat(),))
                conn.commit()
        except: pass

if __name__ == "__main__":
    agent = SovereignIronBotV85()
    agent.handle_mentions()
    agent.post_elite_scoop()
