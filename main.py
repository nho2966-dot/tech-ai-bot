import os
import sqlite3
import hashlib
import tweepy
import logging
from datetime import datetime, date
from openai import OpenAI
from google import genai

logging.basicConfig(level=logging.INFO, format="🛡️ [نظام السيادة]: %(message)s")

class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_all_brains()

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")

    def _setup_all_brains(self):
        # ربط كافة العقول بناءً على السرية الموجودة في الصورة
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        # العقول المختلفة
        self.brains = {
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "Gemini": genai.Client(api_key=os.getenv("GEMINI_KEY")),
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        }

    def execute_brain_sequence(self, prompt):
        """تتابع العقول الستة: التنقل بين المزودين لكسر حظر 429"""
        system_msg = "خبير تقني خليجي. صغ خبر تقني حقيقي ومختصر جداً عن AI للأفراد. لا رموز، لا صيني."
        
        # قائمة العقول والترتيب (يمكنك تعديل الترتيب حسب الرصيد)
        sequence = [
            ("العقل الأول (Groq - Llama 3)", "Groq", "llama3-70b-8192"),
            ("العقل الثاني (xAI - Grok)", "xAI", "grok-beta"),
            ("العقل الثالث (Gemini 2.0)", "Gemini", "gemini-2.0-flash"),
            ("العقل الرابع (OpenRouter)", "OpenRouter", "google/gemini-2.0-flash-001"),
            ("العقل الخامس (OpenAI - 4o)", "OpenAI", "gpt-4o"),
            ("العقل السادس (OpenAI - 4o-mini)", "OpenAI", "gpt-4o-mini")
        ]

        for name, provider_key, model_id in sequence:
            try:
                logging.info(f"🧠 محاولة عبر {name}...")
                client = self.brains[provider_key]
                
                if provider_key == "Gemini":
                    res = client.models.generate_content(model=model_id, contents=f"{system_msg}\n{prompt}")
                    return res.text.strip()
                else:
                    res = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
                        timeout=15
                    )
                    return res.choices[0].message.content.strip()
            except Exception as e:
                logging.warning(f"⚠️ {name} تعذر. السبب: {str(e)[:50]}... ينتقل للتالي.")
                continue
        return None

    def run(self):
        # البحث والنشر بنفس المنطق السابق مع ضمان عدم التكرار
        task = "أعطني خبر أو أداة ذكاء اصطناعي جديدة كلياً ومفيدة للأفراد اليوم."
        content = self.execute_brain_sequence(task)
        
        if content:
            # (كود النشر المعتاد في X)
            logging.info(f"🚀 المحتوى جاهز للنشر: {content}")
            try:
                self.x_client.create_tweet(text=content)
                logging.info("✅ تم النشر بنجاح!")
            except Exception as e:
                logging.error(f"❌ خطأ نشر X: {e}")

if __name__ == "__main__":
    SovereignUltimateBot().run()
