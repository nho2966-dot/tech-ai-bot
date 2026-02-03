import os
import sqlite3
import logging
import hashlib
import time
import re
import random
from datetime import datetime, timezone

import tweepy
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

# إعدادات البيئة
load_dotenv()
DB_FILE = "news.db"

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.commit()
        conn.close()

    def _init_clients(self):
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # --- [محرك الوسوم الهجين والذكاء الاصطناعي] ---

    def extract_hybrid_tags(self, title, description, ai_suggested_content=""):
        """استخراج وسوم من العنوان + المحتوى + مقترحات الـ AI لزيادة الانتشار"""
        keywords = {
            "apple": "#آبل #Apple", "iphone": "#آيفون #iPhone", "nvidia": "#انفيديا #Nvidia",
            "ai": "#ذكاء_اصطناعي #AI", "tesla": "#تسلا #Tesla", "leak": "#تسريبات",
            "samsung": "#سامسونج #Samsung", "openai": "#OpenAI", "vision": "#VisionPro",
            "m4": "#AppleSilicon", "m5": "#AppleSilicon", "google": "#Google",
            "meta": "#Meta", "space": "#الفضاء", "crypto": "#عملات_رقمية"
        }
        
        tags = set(["#تقنية", "#سبق_تقني"])
        full_text = (title + " " + description + " " + ai_suggested_content).lower()

        # استخراج الوسوم بناءً على الكلمات المفتاحية
        for key, val in keywords.items():
            if key in full_text:
                for v in val.split(): tags.add(v)

        # استخراج أي هاشتاقات إضافية كتبها الـ AI في رده
        ai_tags = re.findall(r'#\w+', ai_suggested_content)
        for t in ai_tags: tags.add(t)

        return " ".join(list(tags)[:7]) # نكتفي بـ 7 وسوم كحد أقصى

    def calculate_credibility(self, source_name, entry):
        """حساب المصداقية: مصدر (40%) + محتوى (40%) + حداثة (20%)"""
        score = 55
        authority = {"The Verge": 30, "9to5Mac": 25, "MacRumors": 25, "Bloomberg": 35, "Reuters": 35}
        score += authority.get(source_name, 10)
        content = (entry.title + " " + entry.get('description', '')).lower()
        if any(w in content for w in ["official", "confirmed", "announces", "رسمياً"]): score += 20
        if any(w in content for w in ["leak", "rumor", "تسريب", "إشاعة"]): score -= 25
        return round(max(1, min(100, score)) / 10, 1)

    # --- [أنظمة النشر] ---

    def safe_post(self, text, reply_id=None):
        for i in range(3):
            try:
                res = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=reply_id)
                return res.data['id']
            except tweepy.TooManyRequests:
                time.sleep((i + 1) * 60)
            except Exception as e:
                logging.error(f"❌ خطأ: {e}")
                break
        return None

    def ai_ask(self, system_prompt, user_content):
        try:
            res = self.gemini_client.models.generate_content(model='gemini-1.5-flash', contents=f"{system_prompt}\n\n{user_content}")
            return res.text.strip()
        except:
            try:
                res = self.ai_qwen.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}])
                return res.choices[0].message.content.strip()
            except: return None

    def post_thread(self, content, title, description):
        """تقسيم الثريد ودمج الوسوم المستخرجة من كامل المحتوى"""
        raw_parts = re.split(r'\n\s*\d+[\/\.\)]\s*|\n\n', content.strip())
        tweets = [t.strip()import os
import sqlite3
import logging
import hashlib
import time
import re
import random
from datetime import datetime, timezone

import tweepy
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

# إعدادات البيئة
load_dotenv()
DB_FILE = "news.db"

class TechEliteBot:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")
        self._init_db()
        self._init_clients()

    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (hash TEXT PRIMARY KEY, title TEXT, published_at TEXT)")
        conn.commit()
        conn.close()

    def _init_clients(self):
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    # --- [محرك الوسوم الهجين والذكاء الاصطناعي] ---

    def extract_hybrid_tags(self, title, description, ai_suggested_content=""):
        """استخراج وسوم من العنوان + المحتوى + مقترحات الـ AI لزيادة الانتشار"""
        keywords = {
            "apple": "#آبل #Apple", "iphone": "#آيفون #iPhone", "nvidia": "#انفيديا #Nvidia",
            "ai": "#ذكاء_اصطناعي #AI", "tesla": "#تسلا #Tesla", "leak": "#تسريبات",
            "samsung": "#سامسونج #Samsung", "openai": "#OpenAI", "vision": "#VisionPro",
            "m4": "#AppleSilicon", "m5": "#AppleSilicon", "google": "#Google",
            "meta": "#Meta", "space": "#الفضاء", "crypto": "#عملات_رقمية"
        }
        
        tags = set(["#تقنية", "#سبق_تقني"])
        full_text = (title + " " + description + " " + ai_suggested_content).lower()

        # استخراج الوسوم بناءً على الكلمات المفتاحية
        for key, val in keywords.items():
            if key in full_text:
                for v in val.split(): tags.add(v)

        # استخراج أي هاشتاقات إضافية كتبها الـ AI في رده
        ai_tags = re.findall(r'#\w+', ai_suggested_content)
        for t in ai_tags: tags.add(t)

        return " ".join(list(tags)[:7]) # نكتفي بـ 7 وسوم كحد أقصى

    def calculate_credibility(self, source_name, entry):
        """حساب المصداقية: مصدر (40%) + محتوى (40%) + حداثة (20%)"""
        score = 55
        authority = {"The Verge": 30, "9to5Mac": 25, "MacRumors": 25, "Bloomberg": 35, "Reuters": 35}
        score += authority.get(source_name, 10)
        content = (entry.title + " " + entry.get('description', '')).lower()
        if any(w in content for w in ["official", "confirmed", "announces", "رسمياً"]): score += 20
        if any(w in content for w in ["leak", "rumor", "تسريب", "إشاعة"]): score -= 25
        return round(max(1, min(100, score)) / 10, 1)

    # --- [أنظمة النشر] ---

    def safe_post(self, text, reply_id=None):
        for i in range(3):
            try:
                res = self.x_client.create_tweet(text=text, in_reply_to_tweet_id=reply_id)
                return res.data['id']
            except tweepy.TooManyRequests:
                time.sleep((i + 1) * 60)
            except Exception as e:
                logging.error(f"❌ خطأ: {e}")
                break
        return None

    def ai_ask(self, system_prompt, user_content):
        try:
            res = self.gemini_client.models.generate_content(model='gemini-1.5-flash', contents=f"{system_prompt}\n\n{user_content}")
            return res.text.strip()
        except:
            try:
                res = self.ai_qwen.chat.completions.create(model="qwen/qwen-2.5-72b-instruct", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}])
                return res.choices[0].message.content.strip()
            except: return None

    def post_thread(self, content, title, description):
        """تقسيم الثريد ودمج الوسوم المستخرجة من كامل المحتوى"""
        raw_parts = re.split(r'\n\s*\d+[\/\.\)]\s*|\n\n', content.strip())
        tweets = [t.strip()
