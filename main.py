import os
import sys
import time
import yaml
import random
import sqlite3
import pathlib
import requests
import tweepy
import logging
import hashlib
import re
from datetime import datetime
from google import genai

# إعدادات التسجيل - إمبراطورية ناصر التقنية
logging.basicConfig(level=logging.INFO, format="🛡️ [أيبكس]: %(message)s")

class NasserApexBot:
    def __init__(self):
        self.config = self._load_config()
        self._init_db()
        self._init_clients()
        
        # قائمة العمالقة (العرب + العالميين) - نركز على الحسابات النشطة
        self.tech_titans = [
            '7alsabe', 'faisalkuwait', 'OsamaDawi', 'al_khilaifi', 
            'o_alshubrumi', 'salman_it', 'omardizer', 'i_t_news',
            'elonmusk', 'tim_cook', 'sundarpichai', 'MKBHD', 'verge'
        ]
        logging.info("🚀 أيبكس انطلق (وضع الحساب الموثق نشط)")

    def _load_config(self):
        return {
            'bot': {'database_path': 'data/sovereign.db'},
            'prompts': {
                'system_core': "أنت (أيبكس)، خبير تقني خليجي متمكن. ركز على خبايا الأجهزة والذكاء الاصطناعي للأفراد. اللهجة: خليجية عُمانية بيضاء. ممنوع النجوم والرموز تماماً. ممنوع ذكر الهند.",
                'modes': {
                    'HIDDEN_GEM': "اشرح هذا السر التقني بأسلوب خبير (تدري؟) بلهجة خليجية وبدون رموز: {content}",
                    'TITAN_REPLY': "رد بذكاء خليجي مختصر ومفيد على تغريدة هذا العملاق، أضف قيمة تقنية مخفية تجذب المتابعين: {content}",
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
        # حذف كل رموز الـ Markdown لضمان توافقها مع إكس
        text = re.sub(r'[\*\#\_\[\]\(\)\~\`\>]', '', text)
        return " ".join(text.split())

    def _search_tavily(self, query):
        try:
            url = "https://api.tavily.com/search"
            payload = {"api_key": os.getenv("TAVILY_KEY"), "query": query, "search_depth": "smart", "max_results": 2}
            res = requests.post(url, json=payload).json()
            return "\n".join([obj['content'] for obj in res.get('results', [])])
        except: return ""

    def _generate_image(self, prompt_text):
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            img_prompt = self.config['prompts']['IMAGE_PROMPT'].format(content=prompt_text)
            response = client.models.generate_image(model='imagen-3', prompt=img_prompt)
            img_path = "apex_post.png"
            response.save(img_path)
            return img_path
        except: return None

    def generate(self, mode, inp=""):
        sys_p = self.config['prompts']['system_core']
        task_p = self.config['prompts']['modes'][mode].format(content=inp)
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
            res = client.models.generate_content(model='gemini-2.0-flash', contents=f"{sys_p}\n{task_p}")
            return self._clean_text(res.text)
        except: return None

    def run_post_mission(self):
        """النشر الأساسي: خبايا الأجهزة"""
        logging.info("🔎 جاري التنقيب عن خفايا تقنية...")
        queries = ["hidden iOS pro features", "Android system secrets hacks", "AI tools hidden productivity"]
        search_results = self._search_tavily(random.choice(queries))
        
        if search_results:
            tweet_text = self.generate("HIDDEN_GEM", search_results)
            if tweet_text:
                img_path = self._generate_image(tweet_text)
                self.publish_post(tweet_text, img_path)

    def interact_with_titans(self):
        """الرد على العمالقة (استغلال أفضلية الحساب الموثق)"""
        logging.info("🕵️ مراقبة حسابات العمالقة للرد الذكي...")
        random.shuffle(self.tech_titans)
        
        for username in self.tech_titans:
            try:
                user = self.x_client_v2.get_user(username=username)
                if not user or not user.data: continue
                
                tweets = self.x_client_v2.get_users_tweets(id=user.data.id, max_results=5, exclude=['retweets', 'replies'])
                if not tweets or not tweets.data: continue
                
                target = tweets.data[0]
                with sqlite3.connect(self.config['bot']['database_path']) as conn:
                    if conn.execute("SELECT 1 FROM replied WHERE id=?", (str(target.id),)).fetchone(): continue
                
                reply = self.generate("TITAN_REPLY", target.text)
                if reply:
                    # فاصل زمني طبيعي
                    wait = random.randint(45, 120)
                    logging.info(f"⏳ بانتظر {wait} ثانية قبل الرد الموثق على {username}...")
                    time.sleep(wait)
                    
                    self.x_client_v2.create_tweet(text=reply, in_reply_to_tweet_id=target.id)
                    with sqlite3.connect(self.config['bot']['database_path']) as conn:
                        conn.execute("INSERT INTO replied VALUES (?)", (str(target.id),))
                    logging.info(f"✅ تم الرد بنجاح!")
                    return 
            except: continue

    def publish_post(self, text, img_path=None):
        try:
            # الحساب الموثق يسمح بأكثر من 280 حرف، لكن نفضل الاختصار للجمالية
            if len(text) > 500: text = text[:497] + "..."
            
            h = hashlib.sha256(text.encode()).hexdigest()
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                if conn.execute("SELECT 1 FROM history WHERE hash=?", (h,)).fetchone(): return False

            media_id = None
            if img_path and os.path.exists(img_path):
                media = self.x_api_v1.media_upload(img_path)
                media_id = media.media_id

            self.x_client_v2.create_tweet(text=text, media_ids=[media_id] if media_id else None)
            with sqlite3.connect(self.config['bot']['database_path']) as conn:
                conn.execute("INSERT INTO history VALUES (?, ?)", (h, datetime.now()))
            logging.info("🚀 تم النشر بنجاح!")
            return True
        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")
            return False

if __name__ == "__main__":
    bot = NasserApexBot()
    # 1. النشر أولاً
    bot.run_post_mission()
    # 2. فاصل أمان
    gap = random.randint(180, 400)
    logging.info(f"⏳ فاصل أمان طويل: {gap} ثانية...")
    time.sleep(gap)
    # 3. التفاعل مع المشاهير
    bot.interact_with_titans()
