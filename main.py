import os
import json
import feedparser
import tweepy
from datetime import datetime, timedelta


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"❌ Missing required environment variable: {name}")
    return value


# --- مفاتيح X من GitHub Actions ---
API_KEY = require_env("X_API_KEY")
API_SECRET = require_env("X_API_SECRET")
ACCESS_TOKEN = require_env("X_ACCESS_TOKEN")
ACCESS_SECRET = require_env("X_ACCESS_SECRET")
BEARER_TOKEN = require_env("X_BEARER_TOKEN")


# --- إعداد عميل X ---
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    wait_on_rate_limit=True
)


# --- مصادر موثوقة ---
RSS_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.techcrunch.com/feed/",
    "https://www.wired.com/feed/rss"
]

STATE_FILE = "posted_news.json"

# --- سجل المنشورات ---
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
        published_date = (
            datetime(*entry.published_parsed[:6])
            if hasattr(entry, "published_parsed")
            else datetime.now()
        )

        if (
            datetime.now() - published_date <= timedelta(days=7)
            and entry.link not in posted_news
        ):
            news_items.append({
                "title": entry.title.strip(),
                "url": entry.link,
            })


# --- حد النشر اليومي ---
MAX_DAILY_POSTS = 3
to_post = news_items[:MAX_DAILY_POSTS]


# --- النشر ---
for news in to_post:
    tweet = (
        f"🚀 {news['title']}\n"
        f"اقرأ المزيد من المصدر الرسمي:\n{news['url']}\n"
        f"💬 شاركنا رأيك!"
    )[:280]

    try:
        client.create_tweet(text=tweet)
        posted_news.append(news["url"])
        print(f"✅ Published: {news['title']}")
    except Exception as e:
        print(f"❌ Failed: {news['url']} → {e}")


# --- حفظ السجل ---
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(posted_news, f, ensure_ascii=False, indent=2)
