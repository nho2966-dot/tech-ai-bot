import os
import sqlite3
import time
import logging
import random
import feedparser
import tweepy
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
DB_FILE = "news.db"

class TechEliteBot:
    def __init__(self):
        self._init_logging()
        self._init_clients()
        self.init_db()
        self._get_my_id()

    def _init_logging(self):
        logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s | %(message)s")

    def _init_clients(self):
        self.ai_gemini = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.ai_qwen = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"), 
            base_url="https://openrouter.ai/api/v1"
        )
        self.x_client_v2 = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )

    def _get_my_id(self):
        try:
            me = self.x_client_v2.get_me()
            self.my_user_id = me.data.id
        except:
            self.my_user_id = None

    def init_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS news (id INTEGER PRIMARY KEY, link TEXT UNIQUE)")
        conn.close()

    def safe_ai_request(self, title: str, summary: str, is_reply=False) -> str:
        instruction = (
            "أنت خبير تقني. صغ تغريدة عربية بناءً على المعلومات المرفقة فقط.\n"
            "⚠️ قواعد: لا حروف صينية، لا هلوسة، مصطلحات إنجليزية بين قوسين."
        )
        if is_reply:
            instruction = "أنت مساعد ذكي على X. رد بذكاء ودقة تقنية بالعربية فقط."

        prompt = f"المحتوى: {title} {summary}"

        # 1. محاولة جمناي
        try:
            time.sleep(15) 
            res = self.ai_gemini.models.generate_content(
                model="gemini-1.5-flash", 
                contents=f"{instruction}\n\n{prompt}"
            )
            if res.text: return res.text.strip()
        except Exception:
            logging.warning("Gemini Limit... Switching to Qwen")

        # 2. محاولة كوين (تم إصلاح القوس هنا)
        try:
            completion = self.ai_qwen.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role
