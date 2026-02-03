import os
import sqlite3
import logging
import hashlib
import random
import re
from datetime import datetime

import tweepy
import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

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
        conn.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, replied_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS polls (poll_id TEXT PRIMARY KEY, question TEXT, status TEXT)")
        try:
            conn.execute("SELECT replied_at FROM replies LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE replies ADD COLUMN replied_at TEXT")
        conn.commit()
        conn.close()

    def _init_clients(self):
        g_api = os.getenv("GEMINI_KEY")
        self.gemini_client = genai.Client(api_key=g_api, http_options={'api_version': 'v1'}) if g_api else None
        self.ai_qwen = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def ai_ask(self, system_prompt, user_content):
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_prompt}\n\n{user_content}"
            )
            return response.text.strip()
        except:
            try:
                res = self.ai_qwen.chat.completions.create(
                    model="qwen/qwen-2.5-72b-instruct",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                )
                return res.choices[0].message.content.strip()
            except: return None

    def announce_winner(self, winner_handle):
        """إعلان الفائز بصيغ متنوعة واحترافية"""
        templates = [
            f"بكل فخر، نعلن عن فوز المبدع @{winner_handle} بمسابقة الأسبوع التقنية 🏆. إجابة دقيقة تدل على وعي تقني رفيع. تهانينا لك هذا الفوز المستحق، ونلتقي بكم جميعاً في تحدٍ جديد الأربعاء القادم. 🚀🛡️",
            f"ألف مبروك لصديق الحساب @{winner_handle} 🎉! استطاع حسم مسابقة الأسبوع بذكاء وسرعة. شكرًا لكل من شاركنا شغفه، وحظاً أوفر للجميع في مسابقة الأربعاء القادم.. استعدوا جيداً! 🔥💻",
            f"تهانينا للمبدع @{winner_handle} 🎉 بطل مسابقة الأسبوع التقنية. إجابة نموذجية وفوز مستحق! 🥇 ننتظركم الأربعاء القادم في جولة برمجية جديدة. كونوُا في الموعد. ⚡️"
        ]
        chosen_text = random.choice(templates)
        self.x_client.create_tweet(text=chosen_text)

    def post_thread(self, thread_content):
        """خوارزمية القص الذكي لضمان عدم بتر الكلمات"""
        clean_content = re.sub(r'^(1/|1\.|1\))\s*', '', thread_content.strip())
        raw_parts = re.split(r'\n\s*\d+[\/\.\)]\s*', clean_content)
        tweets = []
        for part in raw_parts:
            text = part.strip()
            if len(text) > 10:
                if len(text) > 270: text = text[:267].rsplit(' ', 1)[0] + "..."
                tweets.append(text)

        last_tweet_id = None
        for i, tweet in enumerate(tweets[:5]):
            try:
                formatted_tweet = f"{i+1}/ {tweet}"
                if i == 0:
                    response = self.x_client.create_tweet(text=formatted_tweet)
                else:
                    response = self.x_client.create_tweet(text=formatted_tweet, in_reply_to_tweet_id=last_tweet_id)
                last_tweet_id = response.data['id']
            except: break
        return True

    def run_cycle(self):
        # منع الرد على النفس في المنشن
        self.handle_mentions()
        
        weekday = datetime.now().weekday() # (0=الإثنين, 2=الأربعاء, 6=الأحد)
        
        # --- استطلاع الأحد ---
        if weekday == 6:
            self.create_poll()

        # --- مسابقة الأربعاء ---
        if weekday == 2:
            quiz_prompt = "ابتكر سؤال تقني سهل وممتع للمتابعين. لا تضع الإجابة."
            quiz_text = self.ai_ask("خبير مسابقات تقنية", quiz_prompt)
            if quiz_text:
                self.x_client.create_tweet(text=f"🏆 مسابقة الأسبوع من X-Tech:\n\n{quiz_text}\n\nأول إجابة صحيحة سيتم دعم حسابها وإعلان الفائز! 🚀")

        # --- نشر الأخبار المعتاد (RSS) ---
        system_instruction = """أنت محرر تقني سعودي فخم. حول الخبر إلى Thread احترافي بالعربية (مصطلحات إنجليزية بين قوسين)."""
        # (بقية منطق RSS المعتاد...)
        logging.info("🛡️ تم إنهاء الدورة بنجاح.")

    def handle_mentions(self):
        try:
            my_id = self.x_client.get_me().data.id
            mentions = self.x_client.get_users_mentions(id=my_id, max_results=5, expansions=['author_id']).data
            if not mentions: return
            for tweet in mentions:
                if tweet.author_id == my_id: continue # منع الرد على النفس
                # (منطق الرد المعتاد...)
        except Exception as e: logging.error(f"Mentions Error: {e}")

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.run_cycle()
