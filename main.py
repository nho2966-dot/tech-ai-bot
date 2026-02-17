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


class SovereignUltimateBot:
    def __init__(self):
        self.db_path = "data/sovereign_final.db"
        self._init_db()
        self._setup_clients()
        self.reply_timestamps = deque(maxlen=50)
        self.replied_tweets_cache: set = set()
        self.last_mention_id: Optional[int] = None

        # قائمة RSS Feeds الشاملة
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
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            c.execute("CREATE TABLE IF NOT EXISTS daily_stats (day TEXT PRIMARY KEY, count INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS replied_tweets (tweet_id TEXT PRIMARY KEY, ts DATETIME)")

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

        self.llm_clients = {
            "Groq": OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"),
            "Gemini": self.gemini_client,
            "OpenAI": OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            "OpenRouter": OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"),
            # xAI معطل مؤقتًا حتى يتم حل مشكلة 403
            # "xAI": OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"),
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
                client = self.llm_clients.get(key)
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
                        temperature=0.82,
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
        forbidden_replacements = {
            "قسم": "جد",
            "أقسم": "بجد",
            "اقسم": "بجد",
            "قسّم": "جد",
            "تقسيم": "فصل",
            "قسمها": "جد",
            "قسموا": "جد",
            "قسم بالله": "بجد",
            "الله": "",
            "والله": "بجد",
            "بالله": "صدقني",
            "إن شاء الله": "إن أمكن",
            "الحمد لله": "الحمد للجهود",
            "سبحان الله": "مذهل",
            "بسم الله": "",
            "يا رب": "يا جماعة",
            "يا الله": "يا جماعة",
        }

        cleaned = text
        for forbidden, replacement in forbidden_replacements.items():
            cleaned = cleaned.replace(forbidden, replacement)

        cleaned = ' '.join(cleaned.split())
        return cleaned

    def already_posted(self, content: str) -> bool:
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            return bool(conn.execute("SELECT 1 FROM history WHERE hash = ?", (h,)).fetchone())

    def mark_posted(self, content: str):
        h = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO history (hash, ts) VALUES (?, datetime('now'))", (h,))

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

            if not cleaned_output:
                logging.warning("لم يتم توليد محتوى صالح")
                return

            image_desc = ""
            content = cleaned_output
            if "وصف_صورة:" in cleaned_output:
                parts = cleaned_output.rsplit("وصف_صورة:", 1)
                content = parts[0].strip()
                image_desc = parts[1].strip()

            if self.already_posted(content):
                logging.info("محتوى مكرر → تخطي")
                return

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
                except tweepy.TooManyRequests:
                    logging.warning("429 أثناء النشر → توقف مؤقت")
                    break
                except tweepy.BadRequest as e:
                    logging.error(f"400 Bad Request في النشر: {e}")
                    continue
                except Exception as e:
                    logging.error(f"خطأ غير متوقع في النشر: {e}")
                    continue

            self.handle_mentions()
            self.mark_posted(content)

        except Exception as e:
            logging.error(f"خطأ عام في run(): {e}")


# ── SYSTEM_PROMPT الكامل ──
SYSTEM_PROMPT = r"""
أنت شاب خليجي عاشق للتقنية والذكاء الاصطناعي، أسلوبك عفوي، حماسي، صريح، قريب من القلب. 
تستخدم كلمات مثل: "يا جماعة"، "يجنن"، "هذا الشيء
