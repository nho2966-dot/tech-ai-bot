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

        # 2. محاولة كوين (تم مراجعة صياغة المصفوفة بدقة)
        try:
            completion = self.ai_qwen.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def handle_mentions(self):
        if not self.my_user_id: return
        try:
            mentions = self.x_client_v2.get_users_mentions(id=self.my_user_id, max_results=5)
            if not mentions or not mentions.data: return
            for tweet in mentions.data:
                conn = sqlite3.connect(DB_FILE)
                if conn.execute("SELECT id FROM news WHERE link=?", (f"m_{tweet.id}",)).fetchone():
                    conn.close()
                    continue
                reply = self.safe_ai_request("رد", tweet.text, is_reply=True)
                if reply:
                    self.x_client_v2.create_tweet(text=reply[:280], in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO news (link) VALUES (?)", (f"m_{tweet.id}",))
                    conn.commit()
                conn.close()
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

    def process_and_post(self):
        RSS_FEEDS = ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"]
        random.shuffle(RSS_FEEDS)
        for url in RSS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                conn = sqlite3.connect(DB_FILE)
                # التأكد من عدم تكرار النشر
                res = conn.execute("SELECT id FROM news WHERE link=?", (entry.link,)).fetchone()
                if res:
                    conn.close()
                    continue
                
                tweet_text = self.safe_ai_request(entry.title, getattr(entry, "summary", ""))
                if tweet_text:
                    try:
                        self.x_client_v2.create_tweet(text=tweet_text[:280])
                        conn.execute("INSERT INTO news (link) VALUES (?)", (entry.link,))
                        conn.commit()
                        conn.close()
                        logging.info("✅ Posted successfully")
                        return
                    except Exception as e:
                        logging.error(f"Post Error: {e}")
                        conn.close()
        logging.info("No new news to post.")

if __name__ == "__main__":
    bot = TechEliteBot()
    bot.handle_mentions()
