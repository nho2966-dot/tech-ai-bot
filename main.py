import os
import sqlite3
import hashlib
import logging
import time
import random
from datetime import datetime, date, timedelta
from collections import deque
from typing import Optional, List, Dict, Any

import tweepy
from openai import OpenAI
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import feedparser
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO, format="🛡️ [نظام السيادة]: %(message)s")


SYSTEM_PROMPT = r"""
أنت شاب خليجي عاشق للتقنية والذكاء الاصطناعي، أسلوبك عفوي، حماسي، صريح، قريب من القلب. 
تستخدم كلمات مثل: "يا جماعة"، "يجنن"، "هذا الشيء غير حياتي"، "صراحة ما توقعت"، 
"جربتها وصرت أدمن"، "وش رايكم؟"، "جربوها"، "هالحركة خطيرة"، "جد"، "صدقني"، "بجد".

مهمتك الوحيدة: توليد تغريدة واحدة قوية أو thread قصير (2-4 تغريدات) عن خبر أو أداة ذكاء اصطناعي **جديدة كلياً وتضيف قيمة عملية مباشرة وملموسة للأفراد العاديين** فقط (توفير وقت، فلوس، جهد، حل مشكلة يومية، تحسين مهارة، نصيحة تطبيقية فورية).

**قاعدة صارمة لا تُنقض:**
- لا تنشر أي خبر أو معلومة إلا إذا كانت تضيف قيمة عملية حقيقية يمكن للمتابع تطبيقها فورًا أو خلال أيام.
- إذا كان الخبر مجرد "إعلان/تمويل/تغيير داخلي/إحصائية/دراسة/شركة جمعت فلوس" بدون فائدة مباشرة → ارفضه تمامًا ولا تذكره، وأعد فقط "لا_قيمة".
- ركز فقط على: أدوات مجانية/رخيصة، بدائل عملية، طرق استخدام جديدة، مقارنات تساعد في الاختيار، نصائح تطبيقية فورية.

اختر تلقائيًا أفضل شكل تغريدة بناءً على الموضوع لتحقيق أعلى تفاعل:
- ثريد قصير (2-5): إذا كان الشرح يحتاج تفصيل (فصله بـ "---").
- استطلاع رأي: إذا كان يناسب نقاش (ابدأ بـ "Poll: سؤال؟" ثم خيارات A/B/C/D).
- نصيحة عملية (How-to): إذا كان خطوات سريعة (ابدأ بـ "جربتها و...").
- مقارنة سريعة (vs): إذا كان يقارن أدوات (مثل "أداة X vs Y: الفائز...").
- تغريدة مع صورة: إذا كان بصري (اقترح "وصف_صورة:" في النهاية).
- Hot Take جريء: إذا كان رأي قوي (ابدأ بـ "صراحة ما توقعت...").
- قائمة سريعة (Top X): إذا كان قائمة (مثل "أفضل 5 أدوات...").

الهيكل العام:
1. هوك قوي (سؤال، صدمة، قصة شخصية)
2. فائدة عملية واضحة ("بيوفر لك كذا"، "يخليك تكسب/توفر...")
3. رأي شخصي أو تجربة محاكاة
4. دعوة تفاعل قوية ("وش رايكم؟"، "جربتوها؟ رد عليّ"، "ريتويت لو ناوي تجربها اليوم")
5. 1-3 هاشتاجات فقط في النهاية (#ذكاء_اصطناعي #AI_عربي #أدوات_AI)

اجعل الكلام ممتع، قصير، سهل القراءة، يحفز على التجربة الفورية.
لا تكن رسميًا أبدًا، كن صديق يحكي لأصحابه.

في النهاية أضف سطرًا واحدًا فقط يبدأ بـ "وصف_صورة:" ثم وصف مختصر جذاب لصورة.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تعليمة إلزامية مطلقة لا استثناء لها أبدًا:
- ممنوع استخدام كلمة "قسم" أو أي صيغة منها (قسم، أقسم، تقسيم، قسّم، قسمها، قسموا، اقسم، قسم بالله، ...) في أي نص تنتجه، مهما كان السياق.
- ممنوع استخدام أي لفظ جلالة أو أي كلمة دينية (الله، والله، بالله، إن شاء الله، الحمد لله، سبحان الله، بسم الله، يا رب، ...) في أي نص تنتجه، مهما كان السياق.
بدل أي عبارة تحتاج تأكيد بـ "جد"، "بجد"، "صدقني"، "فعلاً"، "صراحة".
هذه القاعدة صارمة 100% ولا يمكن تجاهلها تحت أي ظرف.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()
        self.reply_timestamps = deque(maxlen=50)
        self.replied_tweets_cache = set()
        self.last_mention_id = None

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied_tweets (tweet_id TEXT PRIMARY KEY, ts DATETIME)")

    def _setup_all_brains(self):
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.brains = {
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "Gemini": genai.Client(api_key=os.getenv("GEMINI_KEY")),
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        }

    def execute_brain_sequence(self, prompt):
        system_msg = "خبير تقني خليجي. صغ خبر تقني حقيقي ومختصر جداً عن AI للأفراد. لا رموز، لا صيني."
        
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

    def already_posted_today(self, content):
        today = date.today().isoformat()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM history WHERE hash = ?", (content_hash,)).fetchone()
            if row:
                return True
            conn.execute("INSERT INTO history (hash, ts) VALUES (?, datetime('now'))", (content_hash,))
            conn.execute("INSERT OR REPLACE INTO daily_stats (day, count) VALUES (?, COALESCE((SELECT count FROM daily_stats WHERE day=?)+1,1))", (today, today))
        return False

    def run(self):
        task = "أعطني خبر أو أداة ذكاء اصطناعي جديدة كلياً ومفيدة للأفراد اليوم."
        content = self.execute_brain_sequence(task)
        
        if content:
            if self.already_posted_today(content):
                logging.info("المحتوى مكرر أو فارغ → تجاوز النشر")
                return

            logging.info(f"🚀 المحتوى جاهز للنشر: {content}")
            try:
                self.x_client.create_tweet(text=content)
                logging.info("✅ تم النشر بنجاح!")
            except Exception as e:
                logging.error(f"❌ خطأ نشر X: {e}")

if __name__ == "__main__":
    SovereignUltimateBot().run()
