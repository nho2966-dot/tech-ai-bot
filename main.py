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
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class SovereignBot:
    def __init__(self, config_path="utils/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)
        self._init_logging()
        self._init_db()
        self._init_clients()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
        self.logger = logging.getLogger('SovereignBot')

    def _init_db(self):
        db_path = self.cfg['bot']['database_path']
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        with sqlite3.connect(db_path, timeout=30) as c:
            c.execute("CREATE TABLE IF NOT EXISTS queue (h TEXT PRIMARY KEY, title TEXT, link TEXT, status TEXT DEFAULT 'PENDING')")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, created_at TEXT)")

    def _init_clients(self):
        # تهيئة X
        try:
            self.x = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET"),
                wait_on_rate_limit=True
            )
            self.logger.info("🛡️ X Client Ready")
        except Exception as e:
            self.logger.critical(f"🛑 X Error: {e}")
            exit(1)

    def is_sleep_time(self):
        now = datetime.now().hour
        start, end = self.cfg['bot'].get('sleep_start', 2), self.cfg['bot'].get('sleep_end', 8)
        return start <= now < end if start < end else now >= start or now < end

    def _brain(self, content, mode):
        sys_rules = self.cfg['prompts']['system_core']
        prompt_tmpl = self.cfg['prompts']['modes'].get(mode, "{content}")
        full_p = f"{sys_rules}\n\nالموضوع: {prompt_tmpl.format(content=content)}"
        
        # محاولة Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(full_p)
                if res.text: return res.text.strip()[:395]
            except Exception as e:
                self.logger.warning(f"🔄 Gemini Failed: {e}")

        # بصمة رقمية فريدة لمنع خطأ التكرار (403 Forbidden)
        sig = hashlib.md5(str(time.time()).encode()).hexdigest()[:3]
        return f"السيادة الرقمية هي ركيزة الاقتصاد الجديد في الثورة الصناعية الرابعة. [{sig}]"

    def _scrape(self, url):
        try:
            r = requests.get(url, headers={'User-Agent': self.cfg['bot']['user_agent']}, timeout=10)
            soup = BeautifulSoup(r.content, 'html.parser')
            return " ".join([p.get_text() for p in soup.find_all('p')[:5]])[:1000]
        except: return ""

    def dispatch(self):
        if self.is_sleep_time(): return
        db_path = self.cfg['bot']['database_path']
        with sqlite3.connect(db_path, timeout=30) as c:
            row = c.execute("SELECT h, title, link FROM queue WHERE status='PENDING' ORDER BY RANDOM() LIMIT 1").fetchone()
            if row:
                text = self._brain(f"{row[1]} - {self._scrape(row[2])}", "POST_DEEP")
                try:
                    time.sleep(random.uniform(30, 90)) # تأخير بشري
                    self.x.create_tweet(text=text)
                    c.execute("UPDATE queue SET status='PUBLISHED' WHERE h=?", (row[0],))
                    c.commit()
                    self.logger.info("🚀 Tweet Sent")
                except Exception as e: self.logger.error(f"❌ X Error: {e}")

    def run(self):
        feed = feedparser.parse(self.cfg['sources']['rss_feeds'][0]['url'])
        with sqlite3.connect(self.cfg['bot']['database_path'], timeout=30) as c:
            for e in feed.entries[:10]:
                h = hashlib.sha256(e.title.encode()).hexdigest()
                c.execute("INSERT OR IGNORE INTO queue (h, title, link) VALUES (?,?,?)", (h, e.title, e.link))
            c.commit()
        self.dispatch()

if __name__ == "__main__":
    SovereignBot().run()
