import os
import sqlite3
import logging
import hashlib
import tweepy
import feedparser
from datetime import datetime, timezone
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class SovereignPro:
    def __init__(self):
        # مصفوفة العقول السداسية (حسب السكرت المعتمد)
        self.config = {
            "groq": os.getenv("GROQ_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "gemini": os.getenv("GEMINI_KEY"),
            "xai": os.getenv("XAI_API_KEY")
        }
        self.db_path = "data/expert_v26.db"
        self._init_db()
        self._setup_x()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY)")

    def _setup_x(self):
        """الربط مع X - دعم التغريدات الطويلة للحساب المدفوع"""
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def generate_expert_thread(self, title, summary, link):
        """توليد محتوى طويل، متمكن، ومكتمل المعنى (أسلوب كوكتيل ابتكارات)"""
        system_instruction = (
            "أنت مستشار تقني خليجي متمكن. حسابك مدفوع، لذا اكتب محتوى طويلاً وشاملاً (ثريد في تغريدة واحدة). "
            "الهدف: شرح أحدث أدوات الـ AI للأفراد. "
            "الهيكل المعتمد: \n"
            "1. عنوان (Hook) بعبارة 'يا جماعة' أو 'تخيلوا'.\n"
            "2. تقسيم المحتوى لنقاط واضحة (1, 2, 3) مع شرح الفائدة الشخصية.\n"
            "3. اللهجة: خليجية بيضاء راقية.\n"
            "4. الخاتمة: سؤال تفاعلي + دعوة لإعادة التغريد.\n"
            "5. ممنوع اقتطاع الكلام، يجب أن تنتهي الجملة بنقطة ومعنى مكتمل."
        )
        
        user_prompt = f"حول هذا الخبر التقني لثريد إبداعي متكامل للأفراد: {title}. التفاصيل: {summary}. الرابط: {link}"
        
        # نستخدم أقوى العقول المتوفرة للصياغة الطويلة
        for brain in ["openai", "groq", "xai"]:
            key = self.config.get(brain)
            if not key: continue
            try:
                client = OpenAI(api_key=key, base_url={"groq": "https://api.groq.com/openai/v1", "xai": "https://api.x.ai/v1"}.get(brain))
                res = client.chat.completions.create(
                    model={"openai": "gpt-4o", "groq": "llama-3.3-70b-versatile", "xai": "grok-beta"}.get(brain),
                    messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": user_prompt}],
                    temperature=0.7
                )
                return res.choices[0].message.content.strip()
            except: continue
        return None

    def run(self):
        # جلب أخبار الذكاء الاصطناعي للأفراد
        feed = feedparser.parse("https://www.zdnet.com/topic/artificial-intelligence/rss.xml")
        
        for entry in feed.entries[:3]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    thread_content = self.generate_expert_thread(entry.title, entry.summary, entry.link)
                    if thread_content:
                        try:
                            self.x_client.create_tweet(text=thread_content)
                            conn.execute("INSERT INTO history VALUES (?)", (h,))
                            conn.commit()
                            logging.info("🚀 تم نشر الثريد الإبداعي المكتمل!")
                            break 
                        except Exception as e: logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    SovereignPro().run()
