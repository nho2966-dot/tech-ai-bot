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
from openai import OpenAI, OpenAIError

# ───────────────────────────────────────────────
# قراءة الإعدادات من config.yaml (في الجذر)
# ───────────────────────────────────────────────

CONFIG_PATH = "config.yaml"

try:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f)
    print("→ تم تحميل config.yaml بنجاح")
except FileNotFoundError:
    print("× ملف config.yaml غير موجود في الجذر – استخدام قيم افتراضية")
    CONFIG = {}
except yaml.YAMLError as e:
    print(f"× خطأ في تنسيق config.yaml: {e}")
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
# وضع التشغيل (auto / manual)
# ───────────────────────────────────────────────

def parse_bot_mode():
    parser = argparse.ArgumentParser(description="Tech AI Bot")
    parser.add_argument('--mode', choices=['auto', 'manual'], default=CONFIG.get("bot", {}).get("mode", "auto"))
    return parser.parse_args().mode

BOT_MODE = parse_bot_mode()
print(f"→ وضع التشغيل: {BOT_MODE.upper()}")

# ───────────────────────────────────────────────
# ثوابت أخرى
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
# الكلاس الرئيسي (نفس الهيكلة السابقة)
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
        path = STATE_FILE
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
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

    HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)

    def _extract_hashtags(self, text: str):
        tags = ["#" + m.group(1) for m in self.HASHTAG_RE.finditer(text)]
        cleaned = self.HASHTAG_RE.sub("", text).strip()
        return cleaned, tags

    def _apply_hashtags_to_last_tweet(self, tweets: List[str], max_tags: int = 2):
        all_tags = []
        cleaned = []
        for t in tweets:
            c, tags = self._extract_hashtags(t)
            cleaned.append(c)
            all_tags.extend(tags)

        tags_final = (all_tags or DEFAULT_HASHTAGS)[:max_tags]
        tag_line = " ".join(tags_final).strip()

        last = cleaned[-1].rstrip()
        extra = f"\n\n{tag_line}"
        if self.signature:
            extra += f" {self.signature}"

        if len(last + extra) <= TWEET_LIMIT:
            cleaned[-1] = last + extra
        else:
            reserve = len(extra) + 5
            cleaned[-1] = last[:-reserve].rstrip() + "…" + extra

        return cleaned

    def _generate_thread(self) -> Optional[List[str]]:
        pillar, desc = random.choice(list(self.content_pillars.items()))

        prompt = (
            f"اكتب thread تقني عربي احترافي عن: {pillar} — {desc}\n"
            f"افصل بـ: {THREAD_DELIM}\n"
            "- 3–5 تغريدات فقط\n"
            "- كل تغريدة 90–260 حرف\n"
            "- هيكل: جذب → قيمة → سؤال ذكي\n"
            "- لا هاشتاقات داخل النص\n"
            "- أنهِ بسؤال يشجع على التفاعل"
        )

        messages = [
            {"role": "system", "content": self.system_instr},
            {"role": "user", "content": prompt}
        ]

        for model in FALLBACK_MODELS:
            try:
                resp = ai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=900,
                    temperature=0.65
                )
                raw = resp.choices[0].message.content.strip()
                parts = [p.strip() for p in raw.split(THREAD_DELIM) if len(p.strip()) >= 80]
                if 3 <= len(parts) <= 5:
                    return parts
            except Exception as e:
                logging.warning(f"Model {model} failed: {str(e)[:80]}")
                time.sleep(2)

        logging.error("فشل توليد الثريد")
        return None

    def _add_numbering_prefix(self, tweets: List[str]) -> List[str]:
        n = len(tweets)
        if n <= 1:
            return tweets
        return [f"{i}/{n} {t.strip()}" for i, t in enumerate(tweets, 1)]

    def _publish_tweet(self, text: str, reply_to: Optional[str] = None, media_path: Optional[str] = None) -> Dict:
        if self.dry_run:
            logging.info(f"[DRY_RUN] {text[:60]}... (media: {media_path})")
            return {"id": f"dry_{random.randint(10000,99999)}"}

        kwargs = {"text": text, "user_auth": True}
        if reply_to:
            kwargs["in_reply_to_tweet_id"] = reply_to

        if media_path and ENABLE_MEDIA:
            full_path = os.path.join(MEDIA_FOLDER, media_path)
            if os.path.exists(full_path):
                media = client_v2.media_upload(filename=full_path)
                kwargs["media_ids"] = [media.media_id_string]
            else:
                logging.warning(f"Media not found: {media_path}")

        resp = client_v2.create_tweet(**kwargs)
        tid = resp.data["id"]
        self._audit("publish_success", {"id": tid})
        return resp.data

    def _publish_thread(self, tweets: List[str]):
        numbered = self._add_numbering_prefix(tweets)
        final_tweets = self._apply_hashtags_to_last_tweet(numbered)

        if BOT_MODE == 'manual':
            print("\n" + "═" * 70)
            print("الثريد الذي سيُنشر الآن:")
            for i, t in enumerate(final_tweets, 1):
                print(f"\n{i}/{len(final_tweets)}\n{'─' * 50}\n{t}\n")
            print("═" * 70)
            print("→ جاري النشر...\n")
            time.sleep(2.5)

        prev_id = None
        ids = []
        for i, text in enumerate(final_tweets):
            if i > 0:
                self._sleep_jitter(8, 25)

            media = None
            if i == 0 and random.random() < 0.4 and ENABLE_MEDIA:
                media = random.choice(MEDIA_TYPES)

            data = self._publish_tweet(text, prev_id, media)
            prev_id = data["id"]
            ids.append(prev_id)

        self.state["last_thread_time"] = time.time()
        self._save_state()
        print(f"تم نشر الثريد → {len(ids)} تغريدة")
        return ids

    def _should_reply(self, text: str) -> bool:
        return bool(re.search(REPLY_PATTERN, text)) and len(text) > 35

    def _generate_reply(self, mention_text: str) -> str:
        cache_key = mention_text[:120]
        if cache_key in self._reply_cache:
            return self._reply_cache[cache_key]

        prompt = (
            f"رد تقني مختصر (1–3 جمل) مهذب على:\n{mention_text}\n"
            "لا هاشتاقات. كن طبيعيًا."
        )

        messages = [
            {"role": "system", "content": self.system_instr},
            {"role": "user", "content": prompt}
        ]

        reply = ""
        for model in FALLBACK_MODELS[:2]:
            try:
                resp = ai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=140,
                    temperature=0.65
                )
                reply = resp.choices[0].message.content.strip()
                reply = re.sub(r"#\w+", "", reply).strip()[:TWEET_LIMIT - 10]
                self._reply_cache[cache_key] = reply
                return reply
            except:
                continue

        return "شكرًا على سؤالك! هل يمكنك توضيح المشكلة أكثر؟"

    def _interact(self):
        if self._replies_today >= MAX_REPLIES_PER_DAY:
            return

        me = client_v2.get_me(user_auth=True).data
        since_id = self.state.get("last_mention_id")

        mentions = client_v2.get_users_mentions(
            id=me.id, since_id=since_id, max_results=5, user_auth=True
        )

        if not mentions.data:
            return

        replied = 0
        max_seen = None

        for tweet in mentions.data:
            max_seen = max(max_seen or int(tweet.id), int(tweet.id))

            if replied >= MAX_REPLIES_PER_RUN or self._replies_today >= MAX_REPLIES_PER_DAY:
                break

            if not self._should_reply(tweet.text):
                continue

            reply_text = self._generate_reply(tweet.text)

            if BOT_MODE == 'manual':
                print(f"\n→ منشن من @{tweet.author_id[:8]}...")
                print(f"السؤال: {tweet.text[:90]}...")
                print(f"الرد: {reply_text}")
                print("→ جاري النشر...\n")
                time.sleep(1.8)

            media = None
            if random.random() < 0.25 and ENABLE_MEDIA:
                media = random.choice(MEDIA_TYPES)

            self._publish_tweet(reply_text, tweet.id, media)
            self._replies_today += 1
            self.state["replies_today"] = self._replies_today
            replied += 1

        if max_seen:
            self.state["last_mention_id"] = str(max_seen)
            self._save_state()

    def run(self):
        logging.info(f"بدء الدورة - وضع: {BOT_MODE}")

        # محاولة نشر ثريد
        hours_since = (time.time() - self._last_thread_time) / 3600
        if hours_since >= MIN_HOURS_BETWEEN_THREADS:
            thread = self._generate_thread()
            if thread:
                try:
                    self._publish_thread(thread)
                except Exception as e:
                    logging.error(f"فشل نشر الثريد: {str(e)[:120]}")
        else:
            logging.info(f"مبكر لثريد جديد ({hours_since:.1f}h)")

        self._sleep_jitter(4, 12)
        self._interact()

        logging.info("انتهت الدورة")


if __name__ == "__main__":
    bot = TechExpertMasterFinal()
    bot.run()
