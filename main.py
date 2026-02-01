import os
import json
import feedparser
import tweepy
from datetime import datetime, timedelta
from collections import Counter

# ================== الإعدادات ==================
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

STATE_FILE = "posted_news.json"
MAX_DAILY_POSTS = 3
MAX_AGE_DAYS = 7

TRUSTED_SOURCES = [
    "theverge.com",
    "techcrunch.com",
    "wired.com",
    "reuters.com",
    "nature.com",
    "openai.com",
    "googleblog.com",
    "ai.googleblog.com",
    "blogs.nvidia.com"
]

RSS_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://www.reuters.com/technology/rss"
]

# ================== عميل X ==================
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)

# ================== أدوات مساعدة ==================
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ================== التحقق من المصدر ==================
class SourceVerifier:
    @staticmethod
    def is_trusted(url: str) -> bool:
        return any(src in url for src in TRUSTED_SOURCES)

# ================== جلب الأخبار ==================
class NewsCollector:
    def fetch(self):
        items = []
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if not hasattr(entry, "link") or not hasattr(entry, "title"):
                    continue

                if not SourceVerifier.is_trusted(entry.link):
                    continue

                published = (
                    datetime(*entry.published_parsed[:6])
                    if hasattr(entry, "published_parsed")
                    else datetime.now()
                )

                if datetime.now() - published <= timedelta(days=MAX_AGE_DAYS):
                    items.append({
                        "title": entry.title.strip(),
                        "url": entry.link,
                        "date": published
                    })
        return items

# ================== تحليل المحتوى ==================
class ContentAnalyzer:
    @staticmethod
    def detect_topic(title: str) -> str:
        title_lower = title.lower()

        if any(k in title_lower for k in ["chip", "gpu", "device", "iphone", "pixel"]):
            return "device"

        if any(k in title_lower for k in ["model", "gpt", "ai", "openai", "gemini"]):
            return "ai_update"

        if any(k in title_lower for k in ["compare", "vs", "battle"]):
            return "comparison"

        return "general"

# ================== رصد الترند ==================
class TrendDetector:
    @staticmethod
    def extract_keywords(news):
        words = []
        for item in news:
            words.extend(item["title"].lower().split())
        common = Counter(words)
        return [w for w, c in common.items() if c >= 3 and len(w) > 4]

# ================== بناء المنشور ==================
class PostComposer:
    @staticmethod
    def compose(news, topic, trends):
        # 🟦 الطبقة 1: الخبر
        layer1 = f"🔹 {news['title']}"

        # 🟨 الطبقة 2: التبسيط
        layer2 = (
            "ببساطة: هذا التطور يعكس تسارع الاستثمار في تقنيات الذكاء الاصطناعي "
            "وانتقالها من التجارب إلى الاستخدام العملي."
        )

        # 🟥 الطبقة 3: التحليل
        insight = (
            "🔍 ما بين السطور: القيمة الحقيقية لن تتضح فورًا، "
            "بل عند تبنّي هذه التقنية على نطاق واسع."
        )

        # تعزيز الترند
        trend_line = ""
        if trends:
            trend_line = f"\n📊 ضمن ترندات الأسبوع: {', '.join(trends[:2])}"

        post = f"""{layer1}

{layer2}

{insight}
{trend_line}

🔗 المصدر: {news['url']}"""

        return post[:280]

# ================== النشر ==================
class Publisher:
    def __init__(self):
        self.posted = load_state()

    def publish(self, posts):
        count = 0
        for post in posts:
            if post["url"] in self.posted:
                continue

            text = PostComposer.compose(
                post,
                post["topic"],
                post["trends"]
            )

            try:
                client.create_tweet(text=text)
                print(f"✅ Published: {post['title']}")
                self.posted.append(post["url"])
                count += 1
            except Exception as e:
                print(f"❌ Error: {e}")

            if count >= MAX_DAILY_POSTS:
                break

        save_state(self.posted)

# ================== التشغيل ==================
def main():
    collector = NewsCollector()
    analyzer = ContentAnalyzer()
    publisher = Publisher()

    news = collector.fetch()
    trends = TrendDetector.extract_keywords(news)

    enriched = []
    for item in news:
        enriched.append({
            **item,
            "topic": analyzer.detect_topic(item["title"]),
            "trends": trends
        })

    publisher.publish(enriched)

if __name__ == "__main__":
    main()
