# main.py
# نقطة الدخول الرئيسية للبوت التقني
# متوافق مع هيكل الريبو: tech-ai-bot / main.py في الجذر

import os
import re
import json
import time
import random
import logging
import argparse
import yaml
from datetime import datetime, timezone
from typing import List, Optional, Dict

import tweepy
from openai import OpenAI, OpenAIError, RateLimitError

# ───────────────────────────────────────────────
# قراءة config.yaml من داخل .github/workflows/
# ───────────────────────────────────────────────

CONFIG_PATH = ".github/workflows/config.yaml"

try:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f)
    print("→ تم تحميل config.yaml من .github/workflows/ بنجاح")
except FileNotFoundError:
    print(f"× ملف {CONFIG_PATH} غير موجود – استخدام قيم افتراضية")
    CONFIG = {}
except yaml.YAMLError as e:
    print(f"× خطأ في تنسيق config.yaml: {e}")
    CONFIG = {}

# استخراج القيم مع افتراضيات
DRY_RUN = CONFIG.get("bot", {}).get("dry_run", False)
SIGNATURE = CONFIG.get("bot", {}).get("signature", "")
DEFAULT_HASHTAGS = CONFIG.get("content", {}).get("default_hashtags", ["#ذكاء_اصطناعي", "#تقنية"])
ENABLE_MEDIA = CONFIG.get("media", {}).get("enabled", True)

# مسار media نسبي من workflows/ إلى الجذر
MEDIA_FOLDER = os.path.normpath(os.path.join(os.path.dirname(__file__), CONFIG.get("media", {}).get("folder", "../../media/")))
MEDIA_TYPES = CONFIG.get("media", {}).get("files", ["ai_infographic.png"])

MIN_HOURS_BETWEEN_THREADS = CONFIG.get("limits", {}).get("min_hours_between_threads", 24)
MAX_REPLIES_PER_RUN = CONFIG.get("limits", {}).get("max_replies_per_run", 2)
MAX_REPLIES_PER_DAY = CONFIG.get("limits", {}).get("max_replies_per_day", 5)

STATE_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), CONFIG.get("paths", {}).get("state_file", "../../state.json")))
AUDIT_LOG = os.path.normpath(os.path.join(os.path.dirname(__file__), CONFIG.get("paths", {}).get("audit_log", "../../audit_log.jsonl")))

# ───────────────────────────────────────────────
# وضع التشغيل
# ───────────────────────────────────────────────

def parse_bot_mode():
    parser = argparse.ArgumentParser(description="Tech AI Bot")
    parser.add_argument('--mode', choices=['auto', 'manual'], default=CONFIG.get("bot", {}).get("mode", "auto"))
    return parser.parse_args().mode

BOT_MODE = parse_bot_mode()
print(f"→ وضع التشغيل: {BOT_MODE.upper()}")

# ───────────────────────────────────────────────
# ثوابت وإعدادات
# ───────────────────────────────────────────────

TWEET_LIMIT = 280
THREAD_DELIM = "\n───\n"

FALLBACK_MODELS = CONFIG.get("generation", {}).get("models_priority", [
    "qwen/qwen-2.5-32b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-instruct"
])

logging.basicConfig(
    level=getattr(logging, CONFIG.get("logging", {}).get("level", "INFO")),
    format=CONFIG.get("logging", {}).get("format", "%(asctime)s | %(levelname)-5s | %(message)s")
)

# ───────────────────────────────────────────────
# الاتصال بالخدمات
# ───────────────────────────────────────────────

ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv(CONFIG.get("api", {}).get("openrouter", {}).get("api_key_env", "OPENROUTER_API_KEY"))
)

client_v2 = tweepy.Client(
    consumer_key=os.getenv(CONFIG.get("api", {}).get("twitter", {}).get("api_key_env", "X_API_KEY")),
    consumer_secret=os.getenv(CONFIG.get("api", {}).get("twitter", {}).get("api_secret_env", "X_API_SECRET")),
    access_token=os.getenv(CONFIG.get("api", {}).get("twitter", {}).get("access_token_env", "X_ACCESS_TOKEN")),
    access_token_secret=os.getenv(CONFIG.get("api", {}).get("twitter", {}).get("access_secret_env", "X_ACCESS_SECRET")),
    wait_on_rate_limit=True
)

# ───────────────────────────────────────────────
# الكلاس الرئيسي
# ───────────────────────────────────────────────

class TechExpertMasterFinal:
    def __init__(self):
        self.dry_run = DRY_RUN
        self.signature = SIGNATURE
        self.content_pillars = CONFIG.get("content", {}).get("pillars", {
            "الذكاء الاصطناعي": "Generative AI, AI Agents, أخلاقيات الاستخدام"
        })
        self.system_instr = (
            "أنت خبير تقني عربي محترف. اكتب بلغة طبيعية ودقيقة.\n"
            "ممنوع اختلاق بيانات.\n"
            "هيكل: جذب → قيمة → سؤال تفاعلي.\n"
            "لا هاشتاقات داخل النص."
        )
        self.state = self._load_state()
        self._replies_today = self._load_daily_reply_count()
        self._last_thread_time = self.state.get("last_thread_time", 0)
        self._reply_cache = {}

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"last_mention_id": None, "last_thread_time": 0, "replies_today": 0, "reply_reset": ""}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False)

    def _audit(self, event: str, data: dict = None):
        record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, 
