import os
import time
import json
import hashlib
import logging
from datetime import datetime
from typing import List, Optional

import tweepy
import feedparser
from google import genai

# ==============================
# ⚙️ الإعدادات العامة
# ==============================

SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://9to5mac.com/feed/",
]

MAX_POSTS_PER_RUN = 2
POST_DELAY = 60
REPLY_DELAY = 30
STATE_FILE = "state.json"

ALLOWED_KEYWORDS = [
    "AI", "Artificial Intelligence", "OpenAI", "Google", "Gemini",
    "Apple", "Microsoft", "NVIDIA", "AMD",
    "chip", "processor", "GPU",
    "smartphone", "device", "hardware",
    "software", "app", "technology"
]

BLO
