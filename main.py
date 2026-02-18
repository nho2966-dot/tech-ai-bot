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
أنت متخصص تقني عربي دقيق ومنظم، أسلوبك واضح، منطقي، احترافي، مباشر، ومفيد. 
تكتب بلغة عربية سلسة وطبيعية بدون إفراط في العامية أو التكرار.

مهمتك: توليد تغريدة واحدة أو thread قصير (2-4 تغريدات) عن خبر أو أداة ذكاء اصطناعي جديدة وتضيف قيمة عملية واضحة (توفير وقت/تكلفة/جهد، حل مشكلة، طريقة تطبيقية، نصيحة فورية).

**قواعد صارمة لا تُنقض:**
- لا تنشر أي محتوى بدون قيمة عملية ملموسة → إذا لم يكن هناك فائدة مباشرة → أعد فقط "لا_قيمة".
- غيّر الأسلوب، البداية، التعبيرات، والتركيز تمامًا في كل مرة. لا تكرر جمل أو هيكل سابق.
- ممنوع أي تعبير مكرر أو مبالغ فيه (مثل "غير حياتي"، "يجنن"، "هالحركة خطيرة"، "صرت أدمن"، "صراحة ما توقعت").
- ركز على: أدوات مجانية/رخيصة، بدائل عملية، طرق استخدام جديدة، مقارنات، نصائح تطبيقية فورية.
- ممنوع كلمة "قسم" أو أي صيغة منها، وممنوع أي لفظ جلالة أو كلمة دينية نهائيًا.
- ممنوع أي نص صيني أو رموز غير مفهومة.

بنية التغريدة منضمة ومتنوعة دائمًا:
- البداية: جملة افتتاحية دقيقة تجذب (خبر، فائدة، سؤال، مقارنة، رقم مفيد).
- الوسط: شرح القيمة بوضوح (كيف تستفيد، ما اللي بيحصل، خطوات إن وجدت).
- النهاية: دعوة تفاعل منطقية ومتنوعة ("ما رأيكم؟"، "هل استخدمتم شيئًا مشابهًا؟"، "شاركوا رأيكم").

اختر شكلًا مختلفًا في كل مرة:
- تغريدة واحدة منظمة
- thread قصير (فصل بـ "---")
- مقارنة واضحة
- قائمة مختصرة
- نصيحة خطوة بخطوة

اجعل النص منظمًا، واضحًا، قصيرًا، يركز على الفائدة العملية بدون مبالغة أو تكرار.
في النهاية أضف سطرًا واحدًا فقط يبدأ بـ "وصف_صورة:" ثم وصف مختصر مناسب.

إذا كان المحتوى لا يحقق القيمة أو مشابه للسابق → رد فقط بـ "لا_قيمة".
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

    def _setup_clients(self):
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
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE
