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
from functools import lru_cache
import difflib  # لـ Levenshtein-like similarity

import tweepy
from openai import OpenAI
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import feedparser
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO, format="🛡️ [نظام السيادة]: %(message)s")


SYSTEM_PROMPT = r"""
أنت متخصص تقني عربي دقيق وموثوق 100%. مهمتك توليد محتوى تقني فقط بناءً على معلومات حقيقية وموثقة، بدون أي افتراضات أو معلومات غير مؤكدة.

**قواعد إلزامية لا تُنقض أبدًا:**
- لا تختلق أي معلومة، رقم، اسم أداة، تاريخ، أو ميزة غير موجودة فعليًا في الواقع حتى لو بدا منطقيًا.
- إذا لم تكن متأكدًا 100% من معلومة → لا تذكرها، وأعد فقط "لا_معلومات_موثوقة".
- ركز فقط على أدوات ومميزات حقيقية موجودة حاليًا (2026)، مع ذكر مصدرها إن أمكن (مثل "حسب تحديث Android 16" أو "في Gemini 2.5").
- ممنوع التخمين أو "ربما" أو "يُعتقد" أو "من المحتمل" في أي سياق تقني.
- النص يجب أن يكون عربيًا فقط، بدون رموز غريبة أو حروف أجنبية غير مفهومة.
- ممنوع كلمة "قسم" أو أي صيغة منها، وممنوع أي لفظ جلالة أو كلمة دينية.

بنية الرد يجب أن تكون منضمة:
- البداية: حقيقة أو فائدة مثبتة.
- الوسط: شرح واضح + خطوات تطبيقية (إن وجدت).
- النهاية: دعوة تفاعل منطقية ("ما رأيكم؟"، "هل جربتم؟").

في النهاية أضف "وصف_صورة:" + وصف مختصر مناسب فقط إذا كان المحتوى يحتاج صورة.

إذا كان المحتوى يحتوي على أي احتمال هلوسة أو معلومة غير مؤكدة → رد فقط بـ "لا_معلومات_موثوقة".
"""


class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()
        self.reply_timestamps = deque(maxlen=50)
        self.replied_tweets_cache = set()
        self.last_mention_id = None
        self.recent_posts = deque(maxlen=10)
        self.topic_blacklist = deque(maxlen=5)  # مواضيع متكررة محظورة مؤقتًا

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
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.UNICODE)

        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    def detect_hallucination(self, text: str) -> bool:
        hallucination_indicators = [
            r"ربما|من المحتمل|يُعتقد|قد يكون|يُقال|حسب ما أعرف|في اعتقادي|ربما|يبدو|من الممكن",
            r"في 202[7-9]|في المستقبل|قريبًا|سيصدر|سيكون متاح|قيد التطوير",
            r"أداة جديدة لم تُطلق بعد|ميزة غير موجودة|غير رسمي",
        ]

        for pattern in hallucination_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        if "لا_معلومات_موثوقة" in text or "لا_قيمة" in text:
            return True

        return False

    def is_semantic_duplicate(self, new_text: str) -> bool:
        new_lower = new_text.lower().strip()
        new_words = set(re.findall(r'\w+', new_lower))

        # كلمات رئيسية متكررة محظورة (موضوعي)
        forbidden_repeated = ["تخصيص", "ردود", "شات جي بي تي", "شات", "تخصيص ردود", "تجربة المستخدم", "تخصيص الردود"]
        new_has_forbidden = any(kw in new_lower for kw in forbidden_repeated)

        for old_text in self.recent_posts:
            old_lower = old_text.lower().strip()
            old_words = set(re.findall(r'\w+', old_lower))

            common = len(new_words & old_words)
            similarity = common / max(len(new_words), len(old_words)) if new_words and old_words else 0

            old_has_forbidden = any(kw in old_lower for kw in forbidden_repeated)

            # إذا كان الموضوع نفسه (forbidden keywords) + تشابه > 50%
            if new_has_forbidden and old_has_forbidden and similarity > 0.50:
                logging.info("تكرار موضوعي في نفس الفكرة → رفض")
                return True

            # تشابه عام
            if similarity > 0.65:
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

    def fetch_fresh_rss(self, max_per_feed: int = 3, max_age_hours: int = 48) -> List[Dict]:
        articles = []
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        ua = "SovereignBot/1.0 (Arabic Tech News Bot)"

        for url in self.rss_feeds:
            try:
                feed = feedparser.parse(url, agent=ua)
                if feed.bozo:
                    continue

                source = feed.feed.get('title', url.split('//')[1].split('/')[0].replace('www.', ''))

                for entry in feed.entries[:max_per_feed]:
                    pub = entry.get('published_parsed') or entry.get('updated_parsed')
                    if not pub:
                        continue

                    pub_date = date_parser.parse(time.strftime("%Y-%m-%d %H:%M:%S", pub))
                    if pub_date < cutoff:
                        continue

                    title = (entry.get('title') or "").strip()
                    link = (entry.get('link') or "").strip()
                    summary = (entry.get('summary') or entry.get('description') or "")[:280].strip()

                    if not title or not link:
                        continue

                    content_for_hash = f"{title} {link}"
                    if self.already_posted(content_for_hash):
                        continue

                    text_lower = (title + summary).lower()
                    if not any(kw in text_lower for kw in ["أداة", "تطبيق", "توفير", "مجاني", "بديل", "كيف", "طريقة", "استخدم", "جرّب", "أفضل", "نصيحة", "تحسين"]):
                        continue

                    articles.append({
                        "source": source,
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "pub_date": pub_date,
                        "hash": content_for_hash
                    })

            except Exception as e:
                logging.warning(f"فشل {url}: {str(e)[:120]}")

        articles.sort(key=lambda x: x["pub_date"], reverse=True)
        logging.info(f"جلب {len(articles)} خبر جديد ذو قيمة عملية")
        return articles[:8]

    def handle_mentions(self):
        if not self.my_user_id:
            return

        MAX_REPLIES = 2
        count = 0

        try:
            mentions = self.x_client.get_users_mentions(
                id=self.my_user_id,
                since_id=self.last_mention_id,
                max_results=5,
                tweet_fields=['conversation_id', 'author_id', 'created_at']
            )
        except tweepy.TooManyRequests:
            logging.warning("429 Too Many Requests في جلب المنشنات → تخطي")
            return
        except Exception as e:
            logging.error(f"فشل جلب منشنات: {e}")
            return

        if not mentions.data:
            return

        for mention in mentions.data:
            if count >= MAX_REPLIES:
                break

            tid = mention.id
            aid = mention.author_id

            if aid == self.my_user_id:
                continue
            if tid in self.replied_tweets_cache or self.has_replied_to(tid):
                continue
            if not self.can_reply_now():
                continue

            try:
                u = self.x_client.get_user(id=aid, user_fields=['public_metrics'])
                if u.data.public_metrics['followers_count'] < 20:
                    continue
            except:
                continue

            reply_text = self.generate_text(
                f"رد ذكي قصير ومفيد على: '{mention.text}'",
                "رد بأسلوب خليجي عفوي، ذكي، قصير، يضيف قيمة."
            )

            reply_text = self.clean_forbidden_words(reply_text)

            if not reply_text or len(reply_text) > 279:
                continue

            try:
                self.x_client.create_tweet(text=reply_text, in_reply_to_tweet_id=tid)
                self.mark_as_replied(tid)
                self.replied_tweets_cache.add(tid)
                count += 1
                time.sleep(180 + random.randint(0, 120))
            except tweepy.TooManyRequests:
                logging.warning("429 أثناء النشر → توقف مؤقت")
                break
            except Exception as e:
                logging.error(f"فشل رد على {tid}: {e}")

        if mentions.data:
            self.last_mention_id = mentions.data[0].id

    def has_replied_to(self, tweet_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            return bool(conn.execute("SELECT 1 FROM replied_tweets WHERE tweet_id = ?", (tweet_id,)).fetchone())

    def mark_as_replied(self, tweet_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO replied_tweets (tweet_id, ts) VALUES (?, datetime('now'))", (tweet_id,))

    def can_reply_now(self) -> bool:
        now = datetime.utcnow()
        recent = sum(1 for t in self.reply_timestamps if now - t < timedelta(minutes=5))
        if recent >= 5:
            return False
        self.reply_timestamps.append(now)
        return True

    def run(self):
        try:
            fresh_news = self.fetch_fresh_rss(max_per_feed=4, max_age_hours=36)

            context = ""
            if fresh_news:
                local_first = [a for a in fresh_news if any(x in a['source'].lower() for x in ['مصر', 'youm7', 'masrawy', 'اليوم', 'البوابة', 'الوطن', 'سعود', 'إمارات', 'قطر', 'كويت'])]
                top = local_first[0] if local_first else fresh_news[0]

                context = (
                    f"\n\nخبر حديث مهم من {top['source']}:\n"
                    f"{top['title']}\n"
                    f"{top['summary'][:160]}...\nرابط: {top['link']}\n"
                    "استخدمه كإلهام إذا كان يضيف قيمة عملية مباشرة."
                )

            task = f"أعطني خبر أو أداة ذكاء اصطناعي جديدة كلياً ومفيدة للأفراد اليوم.{context}"

            raw_output = self.generate_text(task, SYSTEM_PROMPT)

            cleaned_output = self.clean_forbidden_words(raw_output)

            if "لا_قيمة" in cleaned_output.strip():
                logging.info("المحتوى لا يضيف قيمة عملية → تخطي")
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
