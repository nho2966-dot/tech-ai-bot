import os
import sys
import time
import random
import sqlite3
import requests
import tweepy
import logging
import hashlib
import re
from datetime import datetime
from google import genai

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format="🛡️ [أيبكس]: %(message)s")

class NasserApexBot:
    def __init__(self):
        self.config = self._load_config()
        self._init_db()
        self._init_clients()
        self.tech_titans = [
            '7alsabe', 'faisalkuwait', 'OsamaDawi', 'al_khilaifi', 
            'o_alshubrumi', 'salman_it', 'omardizer', 'i_t_news',
            'elonmusk', 'tim_cook', 'sundarpichai', 'MKBHD'
        ]

    def _load_config(self):
        return {
            'bot': {'database_path': 'data/sovereign.db'},
            'prompts': {
                'system_core': "أنت (أيبكس)، خبير تقني خليجي متمكن. ركز على خبايا الأجهزة والذكاء الاصطناعي للأفراد. اللهجة: خليجية بيضاء. ممنوع النجوم والرموز تماماً.",
                'modes': {
                    'HIDDEN_GEM': "اشرح هذا السر التقني بأسلوب خبير (تدري؟) بلهجة خليجية قوية وبدون رموز: {content}",
                    'TITAN_REPLY': "رد بذكاء خليجي مختصر ومفيد على تغريدة هذا العملاق، أضف قيمة تقنية مخفية: {content}",
                    'IMAGE_PROMPT': "Professional high-tech minimalist 3D illustration of: {content}. No text."
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
            auth = tweepy.OAuth1UserHandler(
                os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
                os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
            )
            self.x_api_v1 = tweepy.API(auth)
            self.x_client_v2 = tweepy.Client(
                bearer_token=os.getenv("X_BEARER_TOKEN"),
                consumer_key=os.getenv("X_API_KEY"),
                consumer_secret=os.getenv("X_API_SECRET"),
                access_token=os.getenv("X_ACCESS_TOKEN"),
                access_token_secret=os.getenv("X_ACCESS_SECRET")
            )
        except Exception as e:
            logging.error(f"❌ خطأ توثيق X: {e}")

    def _clean_text(self, text):
        text = re.sub(r'[\*\#\_\[\]\(\)\~\`\>]', '', text)
        return " ".join(text.split())

    def _search_tavily(self, query):
        try:
            url = "https://api.tavily.com/search"
            payload = {"api_key": os.getenv("TAVILY_KEY"), "query": query, "search_depth": "smart", "max_results": 3}
            res = requests.post(url, json=payload).json()
            return "\n".join([obj['content'] for obj in res.get('results', [])])
        except: return ""

    def generate(self, mode, inp=""):
        sys_p = self.config['prompts']['system_core']
        task_p = self.config['prompts']['modes'][mode].format(content=inp)
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            res = client.models.generate_content(model='gemini-2.0-flash', contents=f"{sys_p}\n{task_p}")
            return self._clean_text(res.text)
        except: return None

    def run_now(self):
        """بدء العمل فوراً بدون تأخير طويل"""
        logging.info("🔥 انطلاق النشر الفوري...")
        
        # 1. البحث والنشر
        queries = ["latest hidden smartphone tricks 2026", "new AI tool features for individuals"]
        results = self._search_tavily(random.choice(queries))
        
        if not results: results = "خبايا تقنية في تحديثات الأنظمة الجديدة تسرع الأداء وتوفر البطارية"
        
        tweet_text = self.generate("HIDDEN_GEM", results)
        if tweet_text:
            # النشر المباشر (نصي حالياً للتأكد من السرعة)
            try:
                self.x_client_v2.create_tweet(text=tweet_text)
                logging.info(f"✅ كفو يا ناصر! التغريدة انتشرت: {tweet_text[:50]}...")
            except Exception as e:
                logging.error(f"❌ فشل النشر المباشر: {e}")

        # 2. فاصل بسيط للردود (30 ثانية فقط للتجربة)
        logging.info("⏳ فاصل قصير قبل الردود...")
        time.sleep(30)
        
        # 3. الرد على العمالقة
        self.interact_with_titans()

    def interact_with_titans(self):
        logging.info("🕵️ مراقبة العمالقة...")
        random.shuffle(self.tech_titans)
        for username in self.tech_titans:
            try:
                user = self.x_client_v2.get_user(username=username)
                tweets = self.x_client_v2.get_users_tweets(id=user.data.id, max_results=5, exclude=['retweets', 'replies'])
                if tweets.data:
                    target = tweets.data[0]
                    reply = self.generate("TITAN_REPLY", target.text)
                    if reply:
                        self.x_client_v2.create_tweet(text=reply, in_reply_to_tweet_id=target.id)
                        logging.info(f"✅ تم الرد على {username}")
                        break
            except: continue

if __name__ == "__main__":
    bot = NasserApexBot()
    bot.run_now()
