import os
import sqlite3
import hashlib
import tweepy
import logging
from datetime import datetime, date
from openai import OpenAI
from google import genai   # ← هذا الـ import الصحيح للمكتبة الجديدة
import time

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
        # Gemini configure مرة واحدة (الطريقة الجديدة)
        try:
            genai.configure(api_key=os.getenv("GEMINI_KEY"))
        except Exception as e:
            logging.error(f"فشل تهيئة Gemini: {e}")

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        self.brains = {
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "Gemini": genai,  # نحفظ الـ genai module مباشرة
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        }

    def already_posted(self, content):
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM history WHERE hash = ?", (content_hash,)).fetchone()
            if row:
                return True
            conn.execute("INSERT INTO history (hash, ts) VALUES (?, datetime('now'))", (content_hash,))
            conn.execute(
                "INSERT OR REPLACE INTO daily_stats (day, count) VALUES (?, COALESCE((SELECT count + 1 FROM daily_stats WHERE day=?), 1))",
                (today, today)
            )
        return False

    def execute_brain_sequence(self, prompt):
        system_msg = "خبير تقني خليجي. صغ خبر تقني حقيقي ومختصر جداً عن AI للأفراد. لا رموز، لا صيني."

        sequence = [
            ("Groq Llama 3.3 70B", "Groq", "llama-3.3-70b-versatile"),
            ("xAI Grok 4.1 Fast Reasoning", "xAI", "grok-4-1-fast-reasoning"),
            ("Gemini 2.5 Flash", "Gemini", "gemini-2.5-flash"),
            ("OpenRouter Gemini 2.5 Flash", "OpenRouter", "google/gemini-2.5-flash"),
            ("OpenAI 4o-mini", "OpenAI", "gpt-4o-mini"),
            ("OpenAI 4o", "OpenAI", "gpt-4o")
        ]

        for name, provider_key, model_id in sequence:
            for attempt in range(1, 4):
                try:
                    logging.info(f"🧠 محاولة {attempt}/3 عبر {name} ({model_id})...")
                    client = self.brains[provider_key]

                    if provider_key == "Gemini":
                        model = client.GenerativeModel(model_id)  # client = genai
                        res = model.generate_content(f"{system_msg}\n{prompt}")
                        text = res.text.strip()
                    else:
                        res = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": system_msg},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7,
                            max_tokens=180,
                            timeout=30
                        )
                        text = res.choices[0].message.content.strip()

                    if text and len(text) > 50:
                        return text

                except Exception as e:
                    err_str = str(e).lower()
                    logging.warning(f"⚠️ {name} فشل (محاولة {attempt}): {err_str[:80]}...")
                    if "429" in err_str or "limit" in err_str or "rate" in err_str:
                        sleep_time = 5 * attempt
                        logging.info(f"   → rate limit → ننتظر {sleep_time} ثواني...")
                        time.sleep(sleep_time)
                        continue
                    elif "502" in err_str or "bad gateway" in err_str:
                        time.sleep(10)
                        continue
                    else:
                        break

        logging.error("❌ كل العقول فشلت.")
        return None

    def run(self):
        task = "أعطني خبر أو أداة ذكاء اصطناعي جديدة كلياً ومفيدة للأفراد اليوم."
        content = self.execute_brain_sequence(task)

        if content:
            if self.already_posted(content):
                logging.info("المحتوى مكرر → تجاوز النشر")
                return

            logging.info(f"🚀 المحتوى جاهز: {content[:100]}...")
            try:
                self.x_client.create_tweet(text=content)
                logging.info("✅ تم النشر بنجاح!")
            except Exception as e:
                logging.error(f"❌ خطأ في النشر: {e}")
        else:
            logging.warning("لم يتم توليد محتوى صالح.")

if __name__ == "__main__":
    SovereignUltimateBot().run()
