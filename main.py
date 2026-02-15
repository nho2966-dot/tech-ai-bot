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
import google.generativeai as genai

load_dotenv()

class SovereignBot:
    def __init__(self, config_path="utils/config.yaml"):
        # تحميل الإعدادات من YAML
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.cfg = yaml.safe_load(f)
            print(f"تم تحميل الإعدادات من: {config_path}")
        except FileNotFoundError:
            print(f"❌ خطأ: ملف الإعدادات غير موجود في {config_path}")
            exit(1)
        except Exception as e:
            print(f"❌ خطأ أثناء قراءة YAML: {e}")
            exit(1)

        self._init_logging()
        self._init_db()

        # تهيئة Google Generative AI إن وجد المفتاح
        google_key = os.getenv(self.cfg['api_keys']['google'])
        if google_key:
            genai.configure(api_key=google_key)
            self.logger.info("تم تهيئة Google Generative AI")

        # تهيئة عميل X (Twitter)
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
            me = self.x.get_me(user_auth=True)
            self.bot_id = str(me.data.id) if me and me.data else None
            self.logger.info(f"🛡️ النظام السيادي متصل | المعرف: {self.bot_id}")
        except Exception as e:
            self.logger.critical(f"⚠️ فشل الاتصال بـ X API: {e}")
            exit(1)

    def _init_logging(self):
        l_cfg = self.cfg['logging']
        logging.basicConfig(
            level=getattr(logging, l_cfg['level']),
            format=l_cfg['format'],
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(l_cfg['name'])

    def _init_db(self):
        db_path = self.cfg['bot']['database_path']
        with sqlite3.connect(db_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")
            c.commit()
        self.logger.info(f"تم تهيئة قاعدة البيانات: {db_path}")

    def _brain(self, content: str = "", mode: str = "POST") -> str:
        sys_rules = self.cfg['prompts']['system_core']
        prompt_template = self.cfg['prompts']['modes'].get(mode, self.cfg['prompts']['modes']['POST'])
        user_prompt = prompt_template.format(content=content)

        rtl = self.cfg['bot']['rtl']

        for model_cfg in self.cfg['models']['priority']:
            api_key = os.getenv(model_cfg['env_key'])
            if not api_key:
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
                        temperature=model_cfg['temperature'],
                        max_tokens=model_cfg['max_tokens'],
                        timeout=model_cfg.get('timeout', 40)
                    )
                    text = res.choices[0].message.content.strip()

                elif model_cfg['type'] == "google":
                    model = genai.GenerativeModel(model_cfg['model'])
                    res = model.generate_content(
                        f"{sys_rules}\n\n{user_prompt}",
                        generation_config=genai.types.GenerationConfig(
                            temperature=model_cfg['temperature'],
                            max_output_tokens=model_cfg['max_output_tokens']
                        )
                    )
                    text = res.text.strip()

                # تنظيف thinking/reasoning tags
                text = re.sub(r'<(thinking|reasoning)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()

                # قص النص مع ترك مساحة للهاشتاجات
                text = text[:235].rstrip()

                # إضافة الهاشتاجات
                final_text = f"{rtl['embed']}{rtl['mark']}{text}{self.cfg['features']['hashtags']['default']}{rtl['pop']}"

                self.logger.info(f"✨ تم التوليد عبر {model_cfg['name']} ({len(final_text)} حرف)")
                return final_text

            except Exception as e:
                self.logger.warning(f"🔄 تجاوز {model_cfg['name']} → {str(e)[:120]}...")
                continue

        # نص احتياطي إذا فشلت كل النماذج
        fallback = f"{rtl['embed']}{rtl['mark']}في زمن الخوارزميات، الوعي هو الثغرة الوحيدة التي لا يمكن اختراقها.{rtl['pop']}"
        return fallback

    def fetch(self):
        headers = {'User-Agent': 'SovereignPeak/2026'}
        for feed in self.cfg['sources']['rss']:
            try:
                resp = requests.get(feed['url'], headers=headers, timeout=15)
                feed_data = feedparser.parse(resp.content)
                for entry in feed_data.entries[:feed.get('max_items', 5)]:
                    title = (entry.title or "").strip()
                    if not title:
                        continue
                    h = hashlib.sha256(title.encode('utf-8')).hexdigest()
                    with sqlite3.connect(self.cfg['bot']['database_path']) as c:
                        c.execute("INSERT OR IGNORE INTO queue (h, title) VALUES (?, ?)", (h, title))
                        c.commit()
                self.logger.info(f"تم جلب {len(feed_data.entries)} عنصر من {feed['url']}")
            except Exception as e:
                self.logger.error(f"فشل جلب {feed['url']}: {e}")

    def handle_interactions(self):
        last_id_str = self._get_meta("last_mention_id", "1")
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id, since_id=last_id_str, max_results=5)
            if not mentions.data:
                return

            new_last_id = last_id_str
            for mention in mentions.data:
                new_last_id = max(new_last_id, str(mention.id))
                with sqlite3.connect(self.cfg['bot']['database_path']) as c:
                    if c.execute("SELECT 1 FROM replies WHERE tweet_id = ?", (str(mention.id),)).fetchone():
                        continue
                    reply_text = self._brain(mention.text, mode="REPLY")
                    if reply_text:
                        self.x.create_tweet(text=reply_text, in_reply_to_tweet_id=mention.id)
                        c.execute("INSERT INTO replies (tweet_id, created_at) VALUES (?, ?)",
                                  (str(mention.id), datetime.now().isoformat()))
                        c.commit()
                        time.sleep(self.cfg['bot']['reply_delay_seconds'])

            self._update_meta("last_mention_id", new_last_id)
            self.logger.info(f"تم معالجة {len(mentions.data)} منشن")
        except Exception as e:
            self.logger.warning(f"مشكلة في معالجة المنشنز: {e}")

    def dispatch(self):
        today = datetime.now().date().isoformat()
        count_str = self._get_meta(f"daily_count_{today}", "0")
        count = int(count_str)

        if count >= self.cfg['bot']['daily_tweet_limit']:
            self.logger.info("تم الوصول إلى الحد اليومي للنشر")
            return

        content = None
        queue_h = None

        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            # أولوية لمنشورات الأدوات إذا كانت مفعلة
            if self.cfg['features']['ai_tools_posts']['enabled'] and random.random() < self.cfg['features']['ai_tools_posts']['probability']:
                topic = random.choice(self.cfg['features']['ai_tools_posts']['topics'])
                content = self._brain(topic, mode="TOOL_POST")
            else:
                row = c.execute("SELECT h, title FROM queue WHERE status = 'PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
                if row:
                    content = self._brain(row[1], "POST")
                    queue_h = row[0]

        if not content or len(content) > 280:
            self.logger.warning("لم يتم توليد محتوى صالح أو تجاوز الحد")
            return

        try:
            # قرار نشر استطلاع رأي
            if random.random() < self.cfg['twitter']['poll']['enabled_probability']:
                poll_cfg = self.cfg['twitter']['poll']
                tweet = self.x.create_tweet(
                    text=content,
                    poll={
                        "options": poll_cfg['default_options'],
                        "duration_minutes": poll_cfg['duration_minutes']
                    }
                )
            else:
                tweet = self.x.create_tweet(text=content)

            self.logger.info(f"تم النشر بنجاح → ID: {tweet.data['id']} | طول: {len(content)}")

            if queue_h:
                c.execute("UPDATE queue SET status = 'PUBLISHED' WHERE h = ?", (queue_h,))
            c.commit()

            self._update_meta(f"daily_count_{today}", str(count + 1))

            # تأخير عشوائي طبيعي
            delay = random.uniform(
                self.cfg['bot']['post_delay']['min_seconds'],
                self.cfg['bot']['post_delay']['max_seconds']
            )
            time.sleep(delay)

        except Exception as e:
            self.logger.error(f"فشل النشر: {e}")

    def _get_meta(self, key: str, default: str = "0") -> str:
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            r = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return r[0] if r else default

    def _update_meta(self, key: str, value: str):
        with sqlite3.connect(self.cfg['bot']['database_path']) as c:
            c.execute("REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
            c.commit()

    def run(self):
        self.logger.info("بدء تشغيل النظام السيادي...")
        self.fetch()
        self.handle_interactions()
        self.dispatch()
        self.logger.info("اكتمل الدورة التشغيلية")

if __name__ == "__main__":
    bot = SovereignBot(config_path="utils/config.yaml")
    bot.run()
