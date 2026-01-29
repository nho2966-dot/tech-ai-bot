import os
import time
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import tweepy
from openai import OpenAI

# =========================
# تحميل الإعدادات
# =========================
load_dotenv()

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
BOT_USER_ID = os.getenv("BOT_USER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

POST_COOLDOWN_SECONDS = 1800
MAX_POSTS_PER_DAY = 3
MAX_NEWS_AGE_SECONDS = 48 * 3600
POST_LOG_FILE = "posted_tweets.json"

# =========================
# تهيئة X و OpenAI Clients
# =========================
client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET,
    wait_on_rate_limit=True
)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# مصادر وكلمات مفتاحية
# =========================
TRUSTED_SOURCES = {
    "openai.com", "google.com", "bbc.com/technology", 
    "techcrunch.com", "wired.com", "arstechnica.com", "theverge.com"
}
TECH_KEYWORDS = [
    "AI", "Artificial Intelligence", "Machine Learning", 
    "Deep Learning", "Neural Network", "ChatGPT", "Robotics", 
    "Smart Devices", "VR", "AR", "IoT", "Quantum"
]
BLOCKED_WORDS = ["اشاعة", "كاذب", "مزيف", "فضائح", "Clickbait"]

# =========================
# أدوات مساعدة
# =========================
def load_posted_log():
    if not os.path.exists(POST_LOG_FILE):
        return {}
    with open(POST_LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posted_log(data):
    with open(POST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_trusted_source(url):
    return any(domain in url for domain in TRUSTED_SOURCES)

def contains_tech_keywords(text):
    return any(keyword.lower() in text.lower() for keyword in TECH_KEYWORDS)

def contains_blocked_words(text):
    return any(word in text for word in BLOCKED_WORDS)

def is_recent_news(news_date_str):
    news_date = datetime.strptime(news_date_str, "%Y-%m-%dT%H:%M:%S")
    return (datetime.utcnow() - news_date).total_seconds() <= MAX_NEWS_AGE_SECONDS

def can_post(content_hash, log):
    if content_hash in log:
        return False
    last_time = log.get("_last_post_time")
    if last_time and (time.time() - last_time) < POST_COOLDOWN_SECONDS:
        return False
    return True

# =========================
# توليد نصائح AI ذكية
# =========================
def generate_ai_tip(news_title):
    prompt = (
        f"اقترح نصيحة تقنية عملية قصيرة وجذابة لمتابعي تغريدات التقنية حول: "
        f"{news_title} بلغة ودودة واحترافية."
    )
    response = ai_client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50
    )
    return response.choices[0].message.content.strip()

# =========================
# أفضل وقت للنشر
# =========================
def get_optimal_post_time():
    hour = datetime.utcnow().hour
    if 9 <= hour < 11:
        return "صباحًا"
    elif 13 <= hour < 15:
        return "بعد الظهر"
    else:
        return "مساءً"

# =========================
# صياغة تغريدة / ثريد
# =========================
def format_tweet(news_item):
    hashtags = "#AI #MachineLearning #SmartDevices #TechNews #Innovation"
    tip = news_item.get("tip") or generate_ai_tip(news_item["title"])
    text = (
        f"{news_item['title']}\n\n💡 نصيحة: {tip}\n\n"
        f"المصدر: {news_item['url']}\n{hashtags}\n"
        f"🕒 أفضل وقت للنشر: {get_optimal_post_time()}"
    )
    return text

# =========================
# نشر التغريدة أو الثريد
# =========================
def publish_tweet(text, in_reply_to_tweet_id=None, media_ids=None):
    response = client.create_tweet(
        text=text, in_reply_to_tweet_id=in_reply_to_tweet_id, media_ids=media_ids
    )
    return response.data["id"]

def publish_thread(news_item, thread_texts, media_ids=None):
    previous_tweet_id = None
    for text in thread_texts:
        previous_tweet_id = publish_tweet(text, in_reply_to_tweet_id=previous_tweet_id, media_ids=media_ids)
        time.sleep(2)
    return previous_tweet_id

# =========================
# استطلاعات الرأي
# =========================
def publish_poll(question, options, duration_minutes=1440):
    client.create_tweet(text=question, poll_options=options, poll_duration_minutes=duration_minutes)

# =========================
# الردود الذكية على التعليقات
# =========================
def reply_to_mentions():
    mentions = client.get_users_mentions(BOT_USER_ID, max_results=20).data
    if not mentions:
        return
    for mention in mentions:
        text = mention.text.lower()
        reply_text = None
        if "ai" in text or "ذكاء اصطناعي" in text:
            reply_text = "🤖 مرحبًا! اكتشف آخر أخبار الذكاء الاصطناعي والتقنية عبر حسابنا."
        elif "iot" in text or "أجهزة ذكية" in text:
            reply_text = "📱 تأكد دائمًا من تحديث الأجهزة الذكية للحصول على أفضل أداء وأمان."
        if reply_text:
            client.create_tweet(text=reply_text, in_reply_to_tweet_id=mention.id)
            print(f"💬 تم الرد على التغريدة: {mention.id}")

# =========================
# جلب الأخبار التقنية الرائجة
# =========================
def fetch_trending_tech_news():
    return [
        {
            "title": "OpenAI تطلق تحديث GPT-5 Beta للمطورين",
            "url": "https://www.openai.com/research/gpt-5-beta",
            "category": "AI",
            "date": "2026-01-29T08:00:00"
        },
        {
            "title": "Google تطلق أداة ML جديدة لتطبيقات IoT",
            "url": "https://developers.google.com/ml-toolkit",
            "category": "تقنية",
            "date": "2026-01-28T15:00:00"
        }
    ]

# =========================
# لوحة تحكم تحليلية صغيرة
# =========================
def show_dashboard(posted_log):
    print("\n📊 لوحة تحكم اليوم:")
    total_posts = len([k for k in posted_log if k != "_last_post_time"])
    print(f"عدد التغريدات اليوم: {total_posts}")
    recent_news = list(posted_log.keys())[-3:]
    print("آخر الأخبار المنشورة:")
    for key in recent_news:
        print(f"- {posted_log[key]['tweet_id']} : {key[:50]}...")

# =========================
# التنفيذ الرئيسي
# =========================
def main():
    posted_log = load_posted_log()
    posts_count = 0

    reply_to_mentions()

    news_items = fetch_trending_tech_news()

    for news in news_items:
        if posts_count >= MAX_POSTS_PER_DAY:
            print(f"⚠️ تم الوصول للحد الأقصى للنشر ({MAX_POSTS_PER_DAY})")
            break

        if not is_trusted_source(news["url"]): continue
        if not contains_tech_keywords(news["title"]): continue
        if contains_blocked_words(news["title"]): continue
        if not is_recent_news(news["date"]): continue

        tweet_text = format_tweet(news)
        content_hash = hash_content(tweet_text)

        if not can_post(content_hash, posted_log): continue

        tweet_id = publish_tweet(tweet_text)
        print(f"✅ تم النشر: {news['title']}")
        posts_count += 1

        poll_question = f"ما رأيكم بأحدث التطورات في {news['category']}؟ 🤔"
        poll_options = ["رائع جدًا", "مفيد", "مثير للاهتمام", "لا يهمني"]
        publish_poll(poll_question, poll_options)
        print("📊 تم نشر استطلاع.")

        posted_log[content_hash] = {"tweet_id": tweet_id, "timestamp": datetime.utcnow().isoformat()}
        posted_log["_last_post_time"] = time.time()
        save_posted_log(posted_log)

    show_dashboard(posted_log)

if __name__ == "__main__":
    main()
