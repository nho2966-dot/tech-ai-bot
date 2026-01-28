import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict
import argparse

import tweepy
from openai import OpenAI, OpenAIError, RateLimitError

# ───────────────────────────────────────────────
# إعدادات عامة
# ───────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[logging.StreamHandler()]
)

TWEET_LIMIT = 280
THREAD_DELIM = "\n───\n"
STATE_FILE = "state.json"
AUDIT_LOG = "audit_log.jsonl"
MEDIA_FOLDER = "media/"

# فلترة الردود
REPLY_PATTERN = re.compile(
    r"(?:كيف|ازاي|لماذا|ما\s*(?:هو|أفضل)|وش|خطأ|bug|مشكلة|حل).{0,90}"
    r"(?:python|js|ai|gpt|ذكاء\s*اصطناعي|برمجة|أمن|aws|blockchain)",
    re.IGNORECASE | re.UNICODE
)

# حدود أمان
MIN_HOURS_BETWEEN_THREADS = int(os.getenv("MIN_HOURS_BETWEEN", "24"))
MAX_REPLIES_PER_RUN = int(os.getenv("MAX_REPLIES_PER_RUN", "2"))
MAX_REPLIES_PER_DAY = int(os.getenv("MAX_REPLIES_PER_DAY", "5"))

ENABLE_MEDIA = True
MEDIA_TYPES = ["ai_infographic.png", "python_cheatsheet.jpg", "quick_tip.mp4"]

DEFAULT_HASHTAGS = ["#ذكاء_اصطناعي", "#تقنية"]

# نماذج بالترتيب (الأسرع/الأرخص أولاً)
FALLBACK_MODELS = [
    "qwen/qwen-2.5-32b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-instruct"
]

# ───────────────────────────────────────────────
# تحديد وضع التشغيل
# ───────────────────────────────────────────────

def parse_bot_mode():
    parser = argparse.ArgumentParser(description="Tech Bot - نشر تلقائي مع/بدون عرض مسبق")
    parser.add_argument('--mode', choices=['auto', 'manual'], default='auto',
                        help='auto = نشر صامت | manual = عرض المحتوى قبل النشر ثم نشر تلقائي')
    return parser.parse_args().mode


BOT_MODE = parse_bot_mode()
print(f"→ وضع التشغيل: {BOT_MODE.upper()}")


class TechExpertMasterFinal:
    """
    بوت تقني عربي احترافي
    - يدعم وضعين: auto (نشر صامت) و manual (عرض المحتوى ثم نشر تلقائي)
    - لا يظهر أي إشارة في التغريدات إلى أنها آلية أو يدوية
    """

    def __init__(self):
        self.dry_run = os.getenv("DRY_RUN", "0") == "1"
        self.signature = os.getenv("SIGNATURE", "").strip()

        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        self
