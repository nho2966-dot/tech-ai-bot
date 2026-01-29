import os
import time
import json
import hashlib
import requests
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
client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET,
    wait_on_rate_limit=True
)

# =========================
# مصادر موثوقة فق
