import os
import sqlite3
import logging
import hashlib
import tweepy
import feedparser
from datetime import datetime, date, timezone
from openai import OpenAI
from google import genai

# إعداد السجلات الاحترافية
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class TechSovereignBot:
    def __init__(self):
        # مصفوفة العقول السداسية
        self.keys = {
            "gemini": os.getenv("GEMINI_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "xai": os.getenv("XAI_API_KEY"),
            "qwen": os.getenv("QWEN_API_KEY")
        }
        self.db_path = "data/expert_v26.db"
        self._init_db()
        self._setup_x()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")

    def _setup_x(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def _check_limit(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT count FROM daily_stats WHERE day=?", (today,)).fetchone()
            return res[0] if res else 0

    def _update_limit(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO daily_stats VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET count=count+1", (today,))
            conn.commit()

    def generate_content(self, title, summary, link):
        """نظام الصياغة والمقارنة العميقة"""
        instruction = (
            "أنت مستشار تقني خليجي متمكن. حسابك مدفوع (اكتب حتى 1000 حرف). "
            "المهمة: قارن المنتج/الأداة في الخبر بما قبلها أو بمنافسيها. "
            "الأسلوب: خليجي أبيض، لغة أرقام (2nm, Nits, TFLOPS)، بدون مقدمات مملة. "
            "الهيكل: 1. جملة قوية. 2. مقارنة تقنية دقيقة بالارقام. 3. الزبدة (Verdict). 4. سؤال تفاعلي. "
            "تأكد من اكتمال المعنى تماماً."
        )
        prompt = f"قارن وصغ بأسلوب دسم: {title}. التفاصيل: {summary}. الرابط: {link}"
        
        # محاولة التنفيذ عبر العقول (الأولوية للجودة)
        order = ["openai", "groq", "xai", "gemini"]
        for brain in order:
            key = self.keys.get(brain)
            if not key: continue
            try:
                if brain == "gemini":
                    client = genai.Client(api_key=key)
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=f"{instruction}\n\n{prompt}")
                    return res.text.strip()
                else:
                    base = {"groq": "https://api.groq.com/openai/v1", "xai": "https://api.x.ai/v1"}.get(brain)
                    model = {"openai": "gpt-4o", "groq": "llama-3.3-70b-versatile", "xai": "grok-beta"}.get(brain)
                    client = OpenAI(api_key=key, base_url=base)
                    res = client.chat.completions.create(model=model, messages=[{"role": "system", "content": instruction}, {"role": "user", "content": prompt}])
                    return res.choices[0].message.content.strip()
            except: continue
        return None

    def run(self):
        if self._check_limit() >= 3:
            logging.info("🛡️ تم استهلاك الحد اليومي (3 تغريدات).")
            return

        # البحث عن أحدث الابتكارات للأفراد
        feeds = ["https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "https://techcrunch.com/category/gadgets/feed/"]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                h = hashlib.md5(entry.link.encode()).hexdigest()
                with sqlite3.connect(self.db_path) as conn:
                    if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                        content = self.generate_content(entry.title, entry.summary, entry.link)
                        if content:
                            try:
                                self.x_client.create_tweet(text=content)
                                conn.execute("INSERT INTO history VALUES (?)", (h,))
                                conn.commit()
                                self._update_limit()
                                logging.info("🚀 تم النشر بنجاح!")
                                return
                            except Exception as e: logging.error(f"❌ خطأ X: {e}")

if __name__ == "__main__":
    TechSovereignBot().run()
