import os
import sys
import time
import yaml
import random
import sqlite3
import pathlib
import requests
import feedparser
import tweepy
import logging
import hashlib
import re
from datetime import datetime
from google import genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# إعدادات التسجيل - إمبراطورية ناصر التقنية
logging.basicConfig(level=logging.INFO, format="🛡️ [أيبكس]: %(message)s")

class NasserApexBot:
    def __init__(self):
        self.config = self._load_config()
        self._init_db()
        self._init_clients()
        logging.info("🚀 أيبكس انطلق مع ميزة البحث الذكي (Tavily)")

    def _load_config(self):
        return {
            'bot': {'database_path': 'data/sovereign.db'},
            'models': {
                'priority': [
                    {'name': 'Gemini', 'type': 'google', 'model': 'gemini-2.0-flash', 'env_key': 'GEMINI_KEY'},
                    {'name': 'Grok', 'type': 'xai', 'model': 'grok-beta', 'env_key': 'XAI_API_KEY'}
                ]
            },
            'prompts': {
                'system_core': "أنت (أيبكس)، خبير تقني خليجي. ركز على الذكاء الاصطناعي للأفراد. استخدم لهجة خليجية بيضاء. ممنوع النجوم والرموز. ممنوع لغات آسيوية أو ذكر الهند.",
                'modes': {
                    'SCOOP': "حلل نتائج البحث هذه واكتب خبر حصري للأفراد بلهجة خليجية: {content}",
                    'REPLY': "رد بذكاء واختصار خليجي بدون رموز: {content}"
                }
            }
        }

    def _init_db(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.config['bot']['database_path']) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS history (hash TEXT PRIMARY KEY, ts DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS replied (id TEXT PRIMARY KEY)")

    def _init_clients(self):
        try:
            self.x_client = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
        except Exception as e:
            logging.error(f"❌ خطأ توثيق X: {e}")

    def _search_tavily(self, query):
        """ميزة البحث الذكي باستخدام المفتاح الموجود في صورتك"""
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": os.getenv("TAVILY_KEY"),
                "query": query,
                "search_depth": "smart",
                "max_results": 3
            }
            res = requests.post(url, json=payload).json()
            results = [obj['content'] for obj in res.get('results', [])]
            return "\n".join(results)
        except:
            return ""

    def _clean_text(self, text):
        text = re.sub(r'[\*\#\_\[\]\(\)\~]', '', text)
        return " ".join(text.split())

    def generate(self, mode, inp=""):
        sys_p = self.config['prompts']['system_core']
        task_p = self.config['prompts']['modes'][mode].format(content=inp)
        
        for m_cfg in self.config['models']['priority']:
            try:
                key = os.getenv(m_cfg['env_key'])
                if not key: continue
                if m_cfg['type'] == "google":
                    client = genai.Client(api_key=key)
                    res = client.models.generate_content(model=m_cfg['model'], contents=f"{sys_p}\n{task_p}")
                    return self._clean_text(res.text)
                else:
                    client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
                    res = client.chat.completions.create(model=m_cfg['model'], messages=[{"role":"user","content":f"{sys_p}\n{task_p}"}])
                    return self._clean_text(res.choices[0].message.content)
            except: continue
        return None

    def handle_mentions(self):
        try:
            me = self.x_client.get_me()
            mentions = self.x_client.get_users_mentions(id=me.data.id, max_results=5)
            if not mentions.data: return
            for tweet in mentions.data:
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM replied WHERE id=?", (str(tweet.id),)).fetchone(): continue
                reply = self.generate("REPLY", tweet.text)
                if reply:
                    self.x_client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO replied VALUES (?)", (str(tweet.id),))
        except: pass

    def run_mission(self):
        # البحث عن أحدث أدوات الذكاء الاصطناعي الشخصية اليوم
        search_results = self._search_tavily("latest AI tools for individuals 2026")
        if search_results:
            content = self.generate("SCOOP", search_results)
            if content: self.publish(content)

    def publish(self, text):
        try:
            h = hashlib.sha256(text.encode()).hexdigest()
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): return False
            self.x_client.create_tweet(text=text)
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
            logging.info("🚀 تم نشر السكوب بنجاح!")
            return True
        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")
            return False

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.handle_mentions()
    bot.run_mission()
