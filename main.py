import os
import json
import feedparser
import tweepy
from datetime import datetime, timedelta

# --- تحميل المتغيرات من GitHub Actions ---
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# إعداد عميل X (تويتر)
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)

# --- مصادر موثوقة للأخبار التقنية ---
RSS_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.techcrunch.com/feed/",
    "https://www.wired.com/feed/rss"
]

STATE_FILE = "posted_news.json"

# تحميل سجل المنشورات
try:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        posted_news = json.load(f)
except FileNotFoundError:
    posted_news = []

# --- جلب الأخبار ---
news_items = []
for feed_url in RSS_FEEDS:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed'):
            published_date = datetime(*entry.published_parsed[:6])
        else:
            published_date = datetime.now()  # في حال عدم وجود تاريخ النشر

        # فلترة الأخبار الجديدة خلال 7 أيام
        if (datetime.now() - published_date) <= timedelta(days=7) and entry.link not in posted_news:
            news_items.append({
                "title": entry.title,
                "url": entry.link,
                "date": published_date.strftime("%Y-%m-%d")
            })

# --- حد أقصى للنشر يوميًا ---
MAX_DAILY_POSTS = 3
to_post = news_items[:MAX_DAILY_POSTS]

# --- نشر الأخبار ---
for news in to_post:
    tweet_text = f"🚀 {news['title']}\nاقرأ المزيد من المصدر الرسمي: {news['url']}\n💬 شاركنا رأيك!"
    tweet_text = tweet_text[:280]  # التأكد من طول التغريدة

    try:
        client.create_tweet(text=tweet_text)
        print(f"تم النشر: {news['title']}")
        posted_news.append(news["url"])
    except Exception as e:
        print(f"خطأ أثناء النشر: {e} - {news['url']}")

# --- تحديث سجل المنشورات ---
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(posted_news, f, ensure_ascii=False, indent=2)
