# main.py
# نقطة الدخول الرئيسية للبوت التقني
# يدعم النشر التلقائي (auto) والعرض قبل النشر (manual)

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
from openai import OpenAI, OpenAIError

# ───────────────────────────────────────────────
# قراءة الإعدادات من config.yaml
# ───────────────────────────────────────────────

CONFIG_PATH = "config.yaml"

try:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f)
    print(f"تم تحميل config.yaml بنجاح")
except Exception as e:
    print(f"خطأ في قراءة config.yaml: {e}")
    CONFIG = {}

# استخراج القيم مع افتراضيات
DRY_RUN = CONFIG.get("bot", {}).get("dry_run", False)
SIGNATURE = CONFIG.get("bot", {}).get("signature", "")
DEFAULT_HASHTAGS = CONFIG.get("content", {}).get("default_hashtags", ["#ذكاء_اصطناعي", "#تقنية"])
ENABLE_MEDIA = CONFIG.get("media", {}).get("enabled", True)
MEDIA_FOLDER = CONFIG.get("media", {}).get("folder", "media/")
MEDIA_TYPES = CONFIG.get("media", {}).get("files", ["ai_infographic.png"])
MIN_HOURS_BETWEEN_THREADS = CONFIG.get("limits", {}).get("min_hours_between_threads", 24)
MAX_REPLIES_PER_RUN = CONFIG.get("limits", {}).get("max_replies_per_run", 2)
MAX_REPLIES_PER_DAY = CONFIG.get("limits", {}).get("max_replies_per_day", 5)

# ───────────────────────────────────────────────
# تحديد وضع التشغيل
# ───────────────────────────────────────────────

def parse_bot_mode():
    parser = argparse.ArgumentParser(description="Tech AI Bot")
    parser.add_argument('--mode', choices=['auto', 'manual'], default=CONFIG.get("bot", {}).get("mode", "auto"))
    return parser.parse_args().mode

BOT_MODE = parse_bot_mode()
print(f"→ وضع التشغيل: {BOT_MODE.upper()}")

# ───────────────────────────────────────────────
# إعدادات أخرى
# ───────────────────────────────────────────────

TWEET_LIMIT = 280
THREAD_DELIM = "\n───\n"
STATE_FILE = CONFIG.get("paths", {}).get("state_file", "state.json")
AUDIT_LOG = CONFIG.get("paths", {}).get("audit_log", "audit_log.jsonl")

FALLBACK_MODELS = CONFIG.get("generation", {}).get("models_priority", [
    "qwen/qwen-2.5-32b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-instruct"
])

logging.basicConfig(
    level=logging.INFO,
    format=CONFIG.get("logging", {}).get("format", "%(asctime)s | %(levelname)-5s | %(message)s")
)

# ───────────────────────────────────────────────
# التهيئة
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
        return {"last_mention_id": None, "last_thread_time": 0, "replies_today": 0}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False)

    def _audit(self, event: str, data: dict = None):
        record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **(data or {})}
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _sleep_jitter(self, min_s=2.0, max_s=18.0):
        time.sleep(min_s + random.random() * (max_s - min_s))

    def _load_daily_reply_count(self):
        today = datetime.now(timezone.utc).date().isoformat()
        reset = self.state.get("reply_reset", today)
        if reset != today:
            self.state["reply_reset"] = today
            self.state["replies_today"] = 0
            self._save_state()
        return self.state.get("replies_today", 0)

    # ── باقي الدوال (توليد الثريد، النشر، الردود) ──
    # يمكنك لصقها من النسخة السابقة مع تعديل المسارات إذا لزم

    def run(self):
        logging.info(f"بدء الدورة - وضع: {BOT_MODE}")
        
        # محاولة نشر ثريد
        if (time.time() - self._last_thread_time) / 3600 >= MIN_HOURS_BETWEEN_THREADS:
            thread = self._generate_thread()
            if thread:
                self._publish_thread(thread)
        
        self._sleep_jitter(4, 12)
        self._interact()
        
        logging.info("انتهت الدورة")

if __name__ == "__main__":
    bot = TechExpertMasterFinal()
    bot.run()
