import os
import time
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import tweepy

# =========================
# تحميل الإعدادات
# =========================
load_dotenv()

X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
BOT_USER_ID = os.getenv("BOT_USER_ID")

POST_COOLDOWN_SECONDS = 1800  # 30 دقيقة
POST_LOG_FILE = "posted_tweets.json"
LOG_FILE = "log.txt"

# =========================
# تسجيل الرسائل
# =========================
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

# =========================
# تحقق من مفاتيح API
# =========================
def check_api_keys():
    missing = []
    if not X_API_KEY or not X_API_SECRET or not X_ACCESS_TOKEN or not X_ACCESS_SECRET:
        missing.append("X/Twitter API keys")
    if missing:
        log(f"❌ مفاتيح API مفقودة: {', '.join(missing)}")
        return False
    log("✅ جميع مفاتيح API موجودة")
    return True

if not check_api_keys():
    exit()

# =========================
# تهيئة X Client
# =========================
try:
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_SECRET,
        wait_on_rate_limit=True
    )
    log("✅ تم تهيئة X Client بنجاح")
except Exception as e:
    log(f"❌ خطأ أثناء تهيئة X Client: {e}")
    exit()

# =========================
# مصادر موثوقة فقط
# =========================
TRUSTED_SOURCES = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "aljazeera.com",
    "who.int",
    "un.org",
    "gov.om",
}

# =========================
# أدوات مساعدة
# =========================
def load_posted_log():
    if not os.path.exists(POST_LOG_FILE):
        return {}
    try:
        with open(POST_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        log("⚠️ خطأ في قراءة posted_tweets.json، سيتم إنشاء سجل جديد")
        return {}

def save_posted_log(data):
    with open(POST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_trusted_source(url):
    return any(domain in url for domain in TRUSTED_SOURCES)

def can_post(content_hash, log):
    if content_hash in log:
        log("⚠️ التغريدة موجودة مسبقًا، لن يتم النشر")
        return False
    last_time = log.get("_last_post_time")
    if last_time:
        elapsed = time.time() - last_time
        if elapsed < POST_COOLDOWN_SECONDS:
            log(f"⏳ يجب الانتظار {int(POST_COOLDOWN_SECONDS - elapsed)} ثانية قبل النشر مجددًا")
            return False
    return True

def format_tweet(title, source):
    return f"{title}\n\nالمصدر: {source}"

def publish_tweet(text):
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data.get("id") if response.data else None
        log(f"✅ تم نشر التغريدة: {text}")
        return tweet_id
    except Exception as e:
        log(f"❌ خطأ أثناء نشر التغريدة: {e}")
        return None

# =========================
# التنفيذ الرئيسي
# =========================
def main():
    log("🚀 بدء تشغيل البوت")
    posted_log = load_posted_log()

    # مثال: بيانات خبر (يمكن لاحقًا الحصولها من API أو RSS)
    news_item = {
        "title": "منظمة الصحة العالمية تعلن عن تحديث جديد لإرشادات الوقاية",
        "url": "https://www.who.int/news/item/example"
    }

    # 1️⃣ تحقق من المصدر
    if not is_trusted_source(news_item["url"]):
        log("❌ مصدر غير موثوق – تم التجاهل")
        return

    # 2️⃣ صياغة التغريدة
    tweet_text = format_tweet(news_item["title"], news_item["url"])
    content_hash = hash_content(tweet_text)

    # 3️⃣ تحقق من النشر
    if not can_post(content_hash, posted_log):
        log("⏳ التغريدة لم تنشر بسبب التكرار أو cooldown")
        return

    # 4️⃣ النشر
    tweet_id = publish_tweet(tweet_text)
    if tweet_id:
        posted_log[content_hash] = {
            "tweet_id": tweet_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        posted_log["_last_post_time"] = time.time()
        save_posted_log(posted_log)
        log("✅ تم تحديث سجل التغريدات")

    log("🚀 انتهاء تشغيل البوت")

if __name__ == "__main__":
    main()
