import os
import sqlite3
import hashlib
import tweepy
import logging
from datetime import datetime, date
from openai import OpenAI
from google import genai
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
        try:
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        except Exception as e:
            logging.error(f"فشل تهيئة Gemini Client: {e}")
            self.gemini_client = None

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        self.brains = {
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "Gemini": self.gemini_client,
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
        system_msg = """
أنت شاب خليجي عاشق للتقنية والذكاء الاصطناعي، أسلوبك عفوي، حماسي، صريح، قريب من القلب. 
تستخدم كلمات مثل: "يا جماعة"، "والله يجنن"، "هذا الشيء غير حياتي"، "صراحة ما توقعت"، 
"جربتها وصرت أدمن"، "وش رايكم؟"، "بالله عليكم جربوها"، "هالحركة خطيرة"، "جد والله"، "صدقني".

مهمتك: توليد تغريدة واحدة قوية أو thread قصير (2-4 تغريدات) عن خبر أو أداة ذكاء اصطناعي جديدة ومفيدة للأفراد اليوم.

الهيكل المفضل الذي ينتشر:
1. هوك قوي جدًا في أول تغريدة (سؤال صاعق، صدمة، قصة شخصية صغيرة، "والله...")
2. شرح سريع + فائدة مباشرة للشخص العادي ("بيوفر لك كذا ساعة"، "يخليك تكسب فلوس بدون...")
3. رأيك الشخصي أو تجربة محاكاة ("جربتها اليوم و...")
4. دعوة تفاعل قوية ("وش رايكم؟"، "جربتوها؟ رد عليّ"، "ريتويت لو ناوي تجربها اليوم")
5. 1-3 هاشتاجات فقط في نهاية آخر تغريدة (مثل #ذكاء_اصطناعي #AI_عربي #أدوات_AI)

إذا كان الموضوع يستاهل thread قصير (2-4 تغريدات)، افصلهم بـ "---" بين كل تغريدة.
اجعل الكلام ممتع، قصير، سهل القراءة، يحفز على الردود والريتويت.
لا تكن رسميًا أبدًا، كن صديق يحكي لأصحابه عن شيء خطير اكتشفه.

في نهاية الرد أضف سطر واحد فقط يبدأ بـ "وصف_صورة:" ثم وصف مختصر وجذاب لصورة يمكن توليدها.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تعليمة إلزامية لا يمكن تجاهلها تحت أي ظرف:
ممنوع تماماً استخدام كلمة "قسم" أو أي صيغة منها (قسم، أقسم، تقسيم، قسّم، قسمها، قسموا، اقسم، قسم بالله، والله أقسم، ...) في أي جزء من الرد أو التغريدات أو الthread أو أي نص تنتجه.
بدلاً من أي عبارة تحتوي على "قسم" استخدم: "والله"، "جد والله"، "صدقني"، "بجد"، "أحلف لك"، "والله العظيم".
لا تستخدم "قسم" بمعنى جزء أو تقسيم أو أي معنى آخر أبداً.
هذه التعليمة مطلقة ولا استثناء لها مهما كان السياق.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        sequence = [
            ("xAI Grok 4.1 Fast Reasoning", "xAI", "grok-4-1-fast-reasoning"),
            ("Groq Llama 3.3 70B", "Groq", "llama-3.3-70b-versatile"),
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
                        if client is None:
                            continue
                        model = client.GenerativeModel(model_id)
                        res = model.generate_content(f"{system_msg}\n{prompt}")
                        text = res.text.strip()
                    else:
                        res = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": system_msg},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.82,
                            max_tokens=420,
                            timeout=35
                        )
                        text = res.choices[0].message.content.strip()

                    if text and len(text) > 80:
                        return text

                except Exception as e:
                    err_str = str(e).lower()
                    logging.warning(f"⚠️ {name} فشل (محاولة {attempt}): {err_str[:80]}...")
                    if any(x in err_str for x in ["429", "limit", "rate", "quota"]):
                        sleep_time = 6 * attempt
                        logging.info(f"   → rate limit → ننتظر {sleep_time} ثواني...")
                        time.sleep(sleep_time)
                        continue
                    elif any(x in err_str for x in ["502", "bad gateway", "timeout"]):
                        time.sleep(8)
                        continue
                    else:
                        break

        logging.error("❌ كل العقول فشلت.")
        return None

    def run(self):
        task = "أعطني خبر أو أداة ذكاء اصطناعي جديدة كلياً ومفيدة للأفراد اليوم."

        raw_output = self.execute_brain_sequence(task)
        if not raw_output:
            logging.warning("لم يتم توليد محتوى صالح.")
            return

        # فصل الوصف الصورة إذا وُجد
        image_desc = ""
        content = raw_output

        if "وصف_صورة:" in raw_output:
            parts = raw_output.rsplit("وصف_صورة:", 1)
            content = parts[0].strip()
            image_desc = parts[1].strip()

        if self.already_posted(content):
            logging.info("المحتوى مكرر → تجاوز النشر")
            return

        # تقسيم إلى thread إذا وُجد الفاصل ---
        tweets = [t.strip() for t in content.split("---") if t.strip()]

        try:
            previous_tweet_id = None
            for i, tweet_text in enumerate(tweets):
                tweet_kwargs = {"text": tweet_text.strip()}

                # صورة فقط في التغريدة الأولى إذا وُجد وصف
                if i == 0 and image_desc:
                    logging.info(f"وصف صورة مقترح للتوليد: {image_desc}")
                    # هنا يمكن إضافة كود رفع/توليد صورة مستقبلاً

                if previous_tweet_id:
                    tweet_kwargs["in_reply_to_tweet_id"] = previous_tweet_id
                    tweet_kwargs["reply_settings"] = "following"

                response = self.x_client.create_tweet(**tweet_kwargs)
                previous_tweet_id = response.data["id"]
                logging.info(f"تم نشر التغريدة {i+1}/{len(tweets)}")

            logging.info("✅ تم النشر بنجاح")
        except Exception as e:
            logging.error(f"خطأ في النشر: {e}")


if __name__ == "__main__":
    SovereignUltimateBot().run()
