import os
import sqlite3
import hashlib
import logging
import time
import random
import re
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
أنت خبير تقني خليجي متخصص في "الذكاء الاصطناعي وأحدث أدواته للأفراد". 
أسلوبك واضح، منظم، احترافي، مباشر، ومفيد.

**قواعد صارمة لا تُنقض:**
- ركز على الوكلاء الأذكياء (AI Agents) والأدوات العملية لعام 2026.
- لا هلوسة، لا كذب، لا افتراضات. إذا لم تجد أداة حقيقية قل "لا_معلومات_موثوقة".
- ممنوع استخدام كلمة "قسم" أو أي لفظ جلالة.
- النص باللغة العربية (لهجة خليجية بيضاء) ولا تستخدم أي رموز غريبة أو لغة صينية.
- الهيكل: فائدة تقنية واضحة → شرح/أداة/خطوات → دعوة تفاعل منطقية.

اختر شكلًا متنوعًا في كل مرة:
- تغريدة واحدة منظمة
- thread قصير (فصل بـ "---")
- مقارنة واضحة
- قائمة مختصرة
- نصيحة خطوة بخطوة

اجعل النص قصيرًا، واضحًا، يركز على الفائدة العملية بدون مبالغة.
في النهاية أضف سطرًا واحدًا فقط يبدأ بـ "وصف_صورة:" ثم وصف مختصر مناسب.

إذا كان المحتوى لا يحقق قيمة عملية أو مشابه للسابق → رد فقط بـ "لا_قيمة".
"""


class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()
        self.reply_timestamps = deque(maxlen=50)
        self.replied_tweets_cache = set()
        self.last_mention_id = None
        self.recent_posts = deque(maxlen=10)  # آخر 10 لمنع التكرار الدلالي

        self.rss_feeds = [
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/",
            "https://www.wired.com/feed/category/science/latest/rss",
            "https://arstechnica.com/category/tech/feed/",
            "https://www.engadget.com/rss.xml",
            "https://www.cnet.com/rss/news/",
            "https://www.technologyreview.com/feed/",
            "https://gizmodo.com/rss",
            "https://venturebeat.com/feed/",
            "https://thenextweb.com/feed",
            "https://www.artificialintelligence-news.com/feed/",
            "https://huggingface.co/blog/feed.xml",
            "https://www.deepmind.com/blog/rss.xml",
            "https://openai.com/blog/rss/",
            "https://www.tech-wd.com/wd-rss-feed.xml",
            "https://www.aitnews.com/feed/",
            "https://www.arageek.com/feed/tech",
            "https://arabhardware.net/feed",
            "https://www.tqniah.net/feed/",
            "https://www.arabtechs.net/feed",
            "https://www.taqniah.com/feed/",
            "https://www.youm7.com/rss/Technologia",
            "https://www.almasryalyoum.com/rss",
            "https://www.masrawy.com/rss/tech",
            "https://www.elbalad.news/rss/tech",
            "https://www.elwatannews.com/rss/section/6",
            "https://www.dostor.org/rss/technology",
            "https://www.vetogate.com/rss/technology",
            "https://www.cairo24.com/rss/technology",
            "https://sabq.org/feed",
            "https://www.aleqt.com/feed",
            "https://aawsat.com/rss/technologia",
            "https://www.okaz.com.sa/rss",
            "https://www.alriyadh.com/page/rss",
            "https://www.alyaum.com/rss",
            "https://www.albayan.ae/tech/rss",
            "https://www.emaratalyoum.com/rss/tech",
            "https://wam.ae/feed/technology",
            "https://qna.org.qa/ar-QA/RSS-Feeds/Technology",
            "https://www.alanba.com.kw/rss/tech",
            "https://kuwaitalyawm.media.gov.kw/rss",
            "https://www.bna.bh/rss",
            "https://omannews.gov.om/rss/technology",
        ]

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied_tweets (tweet_id TEXT PRIMARY KEY, ts DATETIME)")

    def _setup_all_brains(self):
        try:
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        except Exception as e:
            logging.error(f"فشل تهيئة Gemini: {e}")
            self.gemini_client = None

        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        try:
            me = self.x_client.get_me(user_auth=True)
            self.my_user_id = me.data.id
            logging.info(f"Bot user ID: {self.my_user_id}")
        except Exception as e:
            logging.error(f"فشل جلب user ID: {e}")
            self.my_user_id = None

        self.brains = {
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "Gemini": self.gemini_client,
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"),
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=5, max=45),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def generate_text(self, prompt: str, system_msg: str) -> str:
        sequence = [
            ("Groq Llama 3.3", "Groq", "llama-3.3-70b-versatile"),
            ("Gemini Flash", "Gemini", "gemini-2.5-flash"),
            ("OpenAI 4o-mini", "OpenAI", "gpt-4o-mini"),
            ("OpenRouter Gemini", "OpenRouter", "google/gemini-2.5-flash"),
        ]

        for name, key, model in sequence:
            try:
                client = self.brains.get(key)
                if not client:
                    continue

                if key == "Gemini":
                    m = client.GenerativeModel(model)
                    res = m.generate_content(f"{system_msg}\n{prompt}")
                    text = res.text.strip()
                else:
                    res = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.75,
                        max_tokens=420,
                        timeout=40
                    )
                    text = res.choices[0].message.content.strip()

                if text and len(text) > 80:
                    return text

            except Exception as e:
                logging.warning(f"{name} فشل: {str(e)[:100]}")
                continue

        raise RuntimeError("فشل كل النماذج")

    def clean_forbidden_words(self, text: str) -> str:
        forbidden_patterns = [
            r"قسم|أقسم|اقسم|قسّم|تقسيم|قسمها|قسموا|قسم بالله",
            r"الله|والله|بالله|إن شاء الله|الحمد لله|سبحان الله|بسم الله|يا رب|يا الله",
            r"[\u4e00-\u9fff]+",  # صيني
            r"[^\u0600-\u06FF\s0-9a-zA-Z!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]",  # رموز غير عربي/لاتيني/أرقام/ترقيم
        ]

        cleaned = text
        for pattern in forbidden_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.UNICODE)

        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    def is_semantic_duplicate(self, new_text: str) -> bool:
        new_lower = new_text.lower().strip()
        new_words = set(re.findall(r'\w+', new_lower))

        for old_text in self.recent_posts:
            old_lower = old_text.lower().strip()
            old_words = set(re.findall(r'\w+', old_lower))

            common = len(new_words & old_words)
            similarity = common / max(len(new_words), len(old_words)) if new_words and old_words else 0

            if similarity > 0.60:
                logging.info(f"التكرار الدلالي مرتفع ({similarity:.2f}) → رفض")
                return True

        return False

    def already_posted(self, content: str) -> bool:
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            return bool(conn.execute("SELECT 1 FROM history WHERE hash = ?", (h,)).fetchone())

    def mark_posted(self, content: str):
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO history (hash, ts) VALUES (?, datetime('now'))", (h,))
        self.recent_posts.append(content)

    def fetch_current_trends(self):
        """
        جلب أحدث الترندات في المنطقة العربية/الخليجية
        """
        try:
            trends = self.x_client.get_place_trends(woeid=23424938)  # السعودية - يمكن تغيير الـ WOEID
            top_trends = [trend['name'] for trend in trends[0]['trends'][:5] if trend['tweet_volume'] is not None]
            logging.info(f"أحدث الترندات: {top_trends}")
            return top_trends
        except Exception as e:
            logging.error(f"فشل جلب الترندات: {e}")
            return []

    def is_trend_relevant(self, trend: str) -> bool:
        ai_keywords = ["AI", "ذكاء اصطناعي", "ChatGPT", "Grok", "Gemini", "Claude", "تقنية", "تكنولوجيا", "أداة", "رمضان", "صيام", "هاتف", "ساعة", "جهاز"]
        return any(kw.lower() in trend.lower() for kw in ai_keywords)

    def generate_trend_content(self, trend: str):
        task = f"الترند الحالي: {trend}. أنشئ محتوى يربط هذا الترند بأداة ذكاء اصطناعي أو نصيحة تقنية مفيدة عمليًا للأفراد في الحياة اليومية أو رمضان. ركز على القيمة المباشرة (توفير وقت/جهد/مال). استخدم أسلوبًا منضمًا واحترافيًا."
        return self.generate_text(task, SYSTEM_PROMPT)

    def fetch_hidden_gems(self):
        """
        إذا لم يكن هناك ترند أو خبر جديد → ابحث عن خفايا ومميزات الأجهزة الذكية والذكاء الاصطناعي
        """
        hidden_prompt = "ابحث عن خفايا ومميزات مخفية في الأجهزة الذكية أو أدوات الذكاء الاصطناعي التي يجهلها معظم الناس، وركز على ما يقدم قيمة عملية فورية (توفير وقت/مال/جهد). أعطِ أمثلة حقيقية وموثقة."
        return self.generate_text(hidden_prompt, SYSTEM_PROMPT)

    def run(self):
        try:
            # 1. جلب الترندات أولاً
            trends = self.fetch_current_trends()
            selected_trend = None
            for trend in trends:
                if self.is_trend_relevant(trend):
                    selected_trend = trend
                    break

            context = ""
            if selected_trend:
                context += f"\n\nاستغل الترند الحالي: {selected_trend}\nأنشئ محتوى يربطه بأداة AI مفيدة أو نصيحة عملية."

            # 2. جلب أخبار RSS
            fresh_news = self.fetch_fresh_rss(max_per_feed=4, max_age_hours=36)
            if fresh_news:
                top = fresh_news[0]
                context += f"\nخبر حديث: {top['title']} من {top['source']} – {top['summary'][:100]}... {top['link']}"

            # 3. إذا لم يكن هناك ترند أو خبر جديد → ابحث عن خفايا ومميزات
            if not selected_trend and not fresh_news:
                raw_output = self.fetch_hidden_gems()
            else:
                task = f"أعطني محتوى تقني جديد ومفيد للأفراد اليوم.{context}"
                raw_output = self.generate_text(task, SYSTEM_PROMPT)

            cleaned_output = self.clean_forbidden_words(raw_output)

            if "لا_قيمة" in cleaned_output.strip() or "لا_معلومات_موثوقة" in cleaned_output.strip():
                logging.info("المحتوى لا يضيف قيمة أو غير موثوق → تخطي")
                return

            if self.already_posted(cleaned_output):
                logging.info("محتوى مكرر حرفيًا → تخطي")
                return

            if self.is_semantic_duplicate(cleaned_output):
                logging.info("محتوى مشابه دلاليًا → تخطي")
                return

            self.recent_posts.append(cleaned_output)

            image_desc = ""
            content = cleaned_output
            if "وصف_صورة:" in cleaned_output:
                parts = cleaned_output.rsplit("وصف_صورة:", 1)
                content = parts[0].strip()
                image_desc = parts[1].strip()

            tweets = [t.strip() for t in content.split("---") if t.strip()]

            prev_id = None
            for i, txt in enumerate(tweets):
                try:
                    kwargs = {"text": txt}
                    if i == 0 and image_desc:
                        logging.info(f"صورة مقترحة: {image_desc}")
                    if prev_id:
                        kwargs["in_reply_to_tweet_id"] = prev_id
                    resp = self.x_client.create_tweet(**kwargs)
                    prev_id = resp.data["id"]
                    logging.info(f"نشر تغريدة {i+1}/{len(tweets)} بنجاح")
                    time.sleep(5 + random.random() * 10)
                except Exception as e:
                    logging.error(f"خطأ في نشر تغريدة {i+1}: {e}")
                    continue

            self.handle_mentions()
            self.mark_posted(content)

        except Exception as e:
            logging.error(f"خطأ عام في run(): {e}")


if __name__ == "__main__":
    bot = SovereignUltimateBot()
    bot.run()
