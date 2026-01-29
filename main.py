import os
import json
import logging
import random
import tweepy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

STATE_FILE = "state.json"

RESPONSES = [
    "خبر تقني مثير للاهتمام 👏 #ذكاء_اصطناعي",
    "التكنولوجيا تتطور بسرعة مذهلة 🚀",
    "معلومة تقنية رائعة 🤖",
    "المستقبل الرقمي يقترب أكثر 💡",
    "تقدم تقني يستحق المتابعة 🔥"
]

def load_state():
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("replied", [])
    except Exception:
        return []

def save_state(replied):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"replied": replied}, f, ensure_ascii=False, indent=2)

def run_bot():
    logging.info("🚀 بدء تشغيل Tech AI Bot")

    ck = os.getenv("X_API_KEY", "").stri
