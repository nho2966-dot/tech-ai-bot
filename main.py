الكود الذي أرسلته فيه عدة مشاكل فنية وحتى منطقية تجعل من الصعب أن يعمل بشكل صحيح في 2026، خاصة مع تغييرات مكتبات google-generativeai و tweepy وطريقة التعامل مع الـ API.إليك النسخة المصححة والمحسنة والمُختبرة منطقيًا مع تعليقات واضحة على كل تعديل مهم:python

import os
import sqlite3
import hashlib
import time
import random
import re
import logging
import yaml
from datetime import datetime
import tweepy
import feedparser
import requests
from dotenv import load_dotenv
from openai import OpenAI

# في 2026: النسخة الحديثة من مكتبة Google Generative AI
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("تحذير: مكتبة google-generativeai غير مثبتة أو قديمة")
    genai = None
    types = None

load_dotenv()

class SovereignBot:
    def __init__(self, config_path="utils/config.yaml"):
        self.cfg = None
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.cfg = yaml.safe_load(f)
            print(f"✓ تم تحميل الإعدادات من: {config_path}")
        except FileNotFoundError:
            print(f"✗ ملف الإعدادات غير موجود: {config_path}")
            exit(1)
        except yaml.YAMLError as e:
            print(f"✗ خطأ في صيغة YAML: {e}")
            exit(1)
        except Exception as e:
            print(f"✗ خطأ غير متوقع أثناء قراءة الإعدادات: {e}")
            exit(1)

        self._init_logging()
        self._init_db()

        # تهيئة Google GenAI (الطريقة الحديثة 2026)
        self.google_client = None
        google_key = os.getenv(self.cfg['api_keys'].get('google', 'GOOGLE_API_KEY'))
        if google_key and genai is not None:
            try:
                self.google_client = genai.Client(api_key=google_key)
                self.logger.info("✓ تم تهيئة Google Generative AI Client")
            except Exception as e:
                self.logger.error(f"فشل تهيئة Google Client: {e}")

        # تهيئة X (Twitter) Client
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True  # مهم جدًا في 2026
            )
            me = self.x.get_me(user_auth=True)
            self.bot_id = str(me.data.id) if me and me.data else None
            self.logger.info(f"🛡️ متصل بـ X | المعرف: {self.bot_id}")
        except Exception as e:
            self.logger.critical(f"⚠️ فشل الاتصال بـ X API: {e}")
            exit(1)

    def _init_logging(self):
        l_cfg = self.cfg['logging']
        logging.basicConfig(
            level=getattr(logging, l_cfg.get('level', 'INFO')),
            format=l_cfg.get('format', '%(asctime)s | %(levelname)s | %(message)s'),
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(l_cfg.get('name', 'SovereignBot'))

    def _init_db(self):
        db_path = self.cfg['bot']['database_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()
        self.logger.info(f"✓ قاعدة البيانات جاهزة: {db_path}")

    def _brain(self, content: str = "", mode: str = "POST") -> str:
        sys_rules = self.cfg['prompts']['system_core']
        prompt_tmpl = self.cfg['prompts']['modes'].get(mode, self.cfg['prompts']['modes']['POST'])
        user_prompt = prompt_tmpl.format(content=content)

        rtl = self.cfg['bot']['rtl']

        for model_cfg in self.cfg['models']['priority']:
            key_name = model_cfg['env_key']
            api_key = os.getenv(key_name)
            if not api_key:
                self.logger.debug(f"مفتاح {key_name} غير موجود → تخطي {model_cfg['name']}")
                continue

            try:
                text = ""
                if model_cfg['type'] == "openai":
                    client = OpenAI(api_key=api_key, base_url=model_cfg.get('base_url'))
                    res = client.chat.completions.create(
                        model=model_cfg['model'],
                        messages=[
                            {"role": "system", "content": sys_rules},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=model_cfg.get('temperature', 0.7),
                        max_tokens=model_cfg.get('max_tokens', 220),
                        timeout=model_cfg.get('timeout', 45)
                    )
                    text = res.choices[0].message.content.strip()

                elif model_cfg['type'] == "google" and self.google_client:
                    res = self.google_client.models.generate_content(
                        model=model_cfg['model'],
                        config=types.GenerateContentConfig(
                            system_instruction=sys_rules,
                            temperature=model_cfg.get('temperature', 0.7),
                            max_output_tokens=model_cfg.get('max_output_tokens', 220)
                        ),
                        contents=[{"role": "user", "parts": [{"text": user_prompt}]}]
                    )
                    text = res.candidates[0].content.parts[0].text.strip()

                if not text:
                    continue

                # تنظيف
                text = re.sub(r'<(thinking|reasoning|think)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
                text = text[:235].rstrip(' .,!؟')

                final = f"{rtl['embed']}{rtl['mark']}{text}{self.cfg['features']['hashtags']['default']}{rtl['pop']}"
                self.logger.info(f"✓ تم التوليد عبر {model_cfg['name']} ({len(final)} حرف)")
                return final

            except Exception as e:
                self.logger.warning(f"✗ فشل {model_cfg['name']}: {str(e)[:100]}...")
                continue

        fb = f"{rtl['embed']}{rtl['mark']}السيادة ليست في الأدوات… بل في من يملك الوعي ليستخدمها.{rtl['pop']}"
        return fb

    def fetch(self):
        headers = {'User-Agent': self.cfg.get('bot', {}).get('user_agent', 'SovereignBot/2026')}
        for feed_cfg in self.cfg['sources']['rss_feeds']:
            try:
                r = requests.get(feed_cfg['url'], headers=headers, timeout=15)
                r.raise_for_status()
                feed = feedparser.parse(r.content)
                added = 0
                for e in feed.entries[:feed_cfg.get('max_items', 5)]:
                    title = (e.get('title') or "").strip()
                    if not title: continue
                    h = hashlib.sha256(title.encode('utf-8')).hexdigest()
                    with sqlite3.connect(self.cfg['bot']['database_path']) as conn:
                        conn.execute("INSERT OR IGNORE INTO queue (h, title) VALUES (?,?)", (h, title))
                        conn.commit()
                    added += 1
                self.logger.info(f"جلب {added} عنصر من {feed_cfg['url']}")
            except Exception as e:
                self.logger.error(f"فشل {feed_cfg['url']}: {e}")

    def handle_interactions(self):
        last_id = self._get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id, max_results=5)
            if not mentions.data:
                return

            new_last = last_id
            for m in mentions.data:
                new_last = max(new_last, str(m.id))
                with sqlite3.connect(self.cfg['bot']['database_path']) as c:
                    cur = c.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(m.id),))
                    if cur.fetchone():
                        continue
                    reply = self._brain(m.text, "REPLY")
                    if reply:
                        self.x.create_tweet(text=reply, in_reply_to_tweet_id=m.id)
                        c.execute("INSERT INTO replies (tweet_id, created_at) VALUES (?,?)",
                                  (str(m.id), datetime.now().isoformat()))
                        c.commit()
                        time.sleep(self.cfg['bot']['reply_delay_seconds'])
            self._update_meta("last_mention_id", new_last)
            self.logger.info(f"تم معالجة {len(mentions.data)} منشن")
        except Exception as e:
            self.logger.warning(f"خطأ في المنشنز: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count = int(self._get_meta(f"daily_count_{today}", "0"))

        if count >= self.cfg['bot']['daily_tweet_limit']:
            self.logger.info("تم الوصول للحد اليومي")
            return

        content = None
        queue_hash = None

        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            if (self.cfg['features'].get('ai_tools_posts', {}).get('enabled', False) and 
                random.random() < self.cfg['features']['ai_tools_posts'].get('probability', 0.35)):
                topic = random.choice(self.cfg['features']['ai_tools_posts']['topics'])
                content = self._brain(f"أداة في مجال {topic}", "TOOL_POST")
            else:
                row = c.execute("SELECT h, title FROM queue WHERE status='PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
                if row:
                    content = self._brain(row[1], "POST")
                    queue_hash = row[0]

        if not content or len(content) > 280:
            self.logger.warning("محتوى غير صالح أو طويل")
            return

        try:
            poll_cfg = self.cfg['twitter'].get('poll', {})
            if random.random() < poll_cfg.get('enabled_probability', 0.3):
                tweet = self.x.create_tweet(
                    text=content,
                    poll={
                        "options": poll_cfg.get('default_options', ["نعم", "لا", "ربما"]),
                        "duration_minutes": poll_cfg.get('duration_minutes', 1440)
                    }
                )
            else:
                tweet = self.x.create_tweet(text=content)

            self.logger.info(f"نُشر → {tweet.data['id']} | طول: {len(content)}")

            if queue_hash:
                c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (queue_hash,))
            c.commit()

            self._update_meta(f"daily_count_{today}", str(count + 1))

            time.sleep(random.uniform(
                self.cfg['bot']['post_delay']['min_seconds'],
                self.cfg['bot']['post_delay']['max_seconds']
            ))

        except tweepy.TooManyRequests:
            self.logger.warning("Rate limit من X — انتظر 60 ثانية")
            time.sleep(60)
        except Exception as e:
            self.logger.error(f"فشل النشر: {e}")

    def _get_meta(self, key, default="0"):
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key, value):
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
            c.commit()

    def run(self):
        self.logger.info("بدء الدورة السيادية...")
        self.fetch()
        self.handle_interactions()
        self.dispatch()
        self.logger.info("اكتملت الدورة")

if __name__ == "__main__":
    bot = SovereignBot("utils/config.yaml")
    bot.run()

أهم التعديلات والتصحيحات في هذه النسخةدعم حديث لـ google-generativeai (الطريقة الجديدة generate_content مع Client).
user_auth=True في get_me() (مطلوب في tweepy الحديث).
wait_on_rate_limit=True في tweepy.Client (يمنع 429 كثيرًا).
معالجة أفضل للـ exceptions (خاصة rate limit).
تنظيف أكثر أمانًا للنصوص + قص دقيق قبل الهاشتاج.
تسجيل أفضل (logging) مع رسائل عربية واضحة.
دعم كامل لقراءة المسارات والإعدادات من YAML.

الخطوات التالية لتشغيلهاحفظ ملف utils/config.yaml (اللي أعطيتك إياه سابقًا).
تأكد أن .env يحتوي على المفاتيح الصحيحة.
شغّل: python your_script.py
راقب الـ console / logs

إذا ظهر أي خطأ (خاصة في Google GenAI أو tweepy)، انسخ الرسالة وأرسلها لي وسأعدلها فورًا.بالتوفيق يا مهندس السيادة الرقمية! 

