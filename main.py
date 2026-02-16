import os
import logging
import feedparser
import tweepy
from google import genai
from dotenv import load_dotenv

# --- 1. الإعدادات والذاكرة الفائقة ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# --- 2. مفاتيح API ---
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# --- 3. إعداد Twitter API ---
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
)
twitter_api = tweepy.API(auth)

# --- 4. إعداد Google GenAI ---
gemini_client = genai.TextGenerationClient()  # ⚡ الإصلاح الأساسي هنا

# --- 5. مثال على استخدام GenAI ---
def call_gemini(prompt):
    try:
        response = gemini_client.generate_text(
            model="gemini-2.0-flash",
            prompt=prompt
        )
        # بعض الإصدارات قد تحتاج response.result بدل response.text
        return response.text
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return None

# --- 6. قراءة RSS --- 
RSS_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/"
]

def fetch_news():
    articles = []
    for feed in RSS_FEEDS:
        d = feedparser.parse(feed)
        for entry in d.entries[:3]:  # آخر 3 أخبار من كل مصدر
            articles.append({
                "title": entry.title,
                "link": entry.link
            })
    return articles

# --- 7. نشر التغريدات باستخدام الذكاء الاصطناعي ---
def tweet_news():
    news_list = fetch_news()
    for news in news_list:
        prompt = f"اكتب تغريدة جذابة ومختصرة عن الخبر التالي:\n{news['title']}\nرابط: {news['link']}"
        tweet_text = call_gemini(prompt)
        if tweet_text:
            try:
                twitter_api.update_status(tweet_text)
                logging.info(f"✅ تم نشر التغريدة: {tweet_text[:50]}...")
            except Exception as e:
                logging.error(f"خطأ في نشر التغريدة: {e}")
        else:
            logging.warning("تخطي خبر بسبب خطأ في الذكاء الاصطناعي")

# --- 8. تشغيل البوت ---
if __name__ == "__main__":
    logging.info("🚀 بدء تشغيل البوت...")
    tweet_news()
    logging.info("🏁 انتهى التشغيل.")
