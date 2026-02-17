import os
import sqlite3
import logging
import hashlib
import tweepy
import feedparser
from datetime import datetime, timezone
from openai import OpenAI

# إعداد السجلات بهدوء واحترافية
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

class CreativeSovereign:
    def __init__(self):
        # مصفوفة العقول السداسية حسب دستورك (Secrets)
        self.keys = {
            "groq": os.getenv("GROQ_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "gemini": os.getenv("GEMINI_KEY"),
            "xai": os.getenv("XAI_API_KEY"),
            "qwen": os.getenv("QWEN_API_KEY")
        }
        self.db_path = "data/expert_v26.db"
        self._init_db()
        self._setup_x_premium()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY)")

    def _setup_x_premium(self):
        """الربط مع X مع صلاحيات الحساب المدفوع"""
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def generate_creative_content(self, title, summary, link):
        """صياغة إبداعية، مكتملة، وبدون حدود الـ 280 حرف التقليدية"""
        system_instruction = (
            "أنت مستشار تقني خليجي مبدع. حسابك على X مدفوع، لذا خذ راحتك في الشرح (حتى 1000 حرف). "
            "مهمتك: تحويل الخبر التقني إلى 'فائدة ملموسة' للفرد. "
            "الأسلوب: خليجي أبيض، متمكن، وجذاب. \n"
            "القواعد الصارمة: \n"
            "1. ابدأ بعنوان 'قوي' يلفت الانتباه.\n"
            "2. اشرح 'ليش هذا الخبر يهمك كفرد' وكيف تستخدم الأداة.\n"
            "3. لا تنهِ الكلام أبداً في منتصف الجملة، يجب أن يكون المعنى مكتملاً 100%.\n"
            "4. استخدم إيموجيات تعكس الابتكار والذكاء.\n"
            "5. ضع الرابط بوضوح في سطر مستقل في النهاية."
        )
        
        user_prompt = f"الخبر: {title}\nالتفاصيل: {summary}\nالمصدر: {link}"
        
        # اختيار العقل الأنسب (نبدأ بـ OpenAI أو Groq لضمان جودة اللغة الطويلة)
        for brain in ["openai", "groq", "xai"]:
            key = self.keys.get(brain)
            if not key: continue
            try:
                base_url = {"groq": "https://api.groq.com/openai/v1", "xai": "https://api.x.ai/v1"}.get(brain)
                model = {"openai": "gpt-4o", "groq": "llama-3.3-70b-versatile", "xai": "grok-beta"}.get(brain)
                
                client = OpenAI(api_key=key, base_url=base_url)
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.8
                )
                return res.choices[0].message.content.strip()
            except: continue
        return None

    def run(self):
        # التركيز على AI Tools for Individuals
        feed = feedparser.parse("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml")
        
        for entry in feed.entries[:3]:
            h = hashlib.md5(entry.link.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                if not conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone():
                    # نرسل العنوان والملخص للعقل المدبر
                    content = self.generate_creative_content(entry.title, entry.summary, entry.link)
                    if content:
                        try:
                            # النشر كـ Long Tweet لأن الحساب Premium
                            self.x_client.create_tweet(text=content)
                            conn.execute("INSERT INTO history VALUES (?)", (h,))
                            conn.commit()
                            logging.info("🚀 تم نشر محتوى إبداعي متكامل (Long Tweet)!")
                            break 
                        except Exception as e: logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    CreativeSovereign().run()
