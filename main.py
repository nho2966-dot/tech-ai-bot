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

# =========================
# تهيئة X Client
# =========================
def create_client():
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET,
            wait_on_rate_limit=True
        )
        # اختبار صحة التوكن
        client.get_user(id=BOT_USER_ID)
        return client
    except tweepy.errors.Unauthorized:
        print("❌ خطأ: بيانات اعتماد X غير صحيحة. تحقق من Secrets و BOT_USER_ID.")
        return None

client = create_client()
if client is None:
    exit(1)  # إيقاف البوت إذا كان التوكن غير صالح

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

# =========================
# التحقق من إمكانية النشر
# =========================
def can_post(content_hash, log):
    if content_hash in log:
        return False
    last_time = log.get("_last_post_time")
    if last_time:
        elapsed = time.time() - last_time
        if elapsed < POST_COOLDOWN_SECONDS:
            return False
    return True

# =========================
# صياغة المحتوى
# =========================
def format_tweet(title, url):
    return f"{title}\n\nالمصدر: {url}"

# =========================
# النشر الآمن
# =========================
def publish_tweet(client, text):
    try:
        response = client.create_tweet(text=text)
        print(f"✅ تم النشر بنجاح: {response.data['id']}")
        return response.data["id"]
    except tweepy.errors.Unauthorized:
        print("❌ خطأ: فشل النشر بسبب بيانات اعتماد غير صحيحة.")
        return None
    except Exception as e:
        print(f"❌ خطأ غير متوقع عند النشر: {e}")
        return None

# =========================
# منطق التنفيذ الرئيسي
# =========================
def main():
    posted_log = load_posted_log()

    # مثال: بيانات خبر تقني حديث
    news_items = [
        {
            "title": "شركة آبل تكشف عن تحديث iOS 18 مع مزايا ذكاء اصطناعي محسّنة",
            "url": "https://www.apple.com/newsro
