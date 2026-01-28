import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone
from functools import lru_cache, wraps
from typing import List, Optional, Dict

import tweepy
from openai import OpenAI, OpenAIError, RateLimitError

# ----------------------------
# إعدادات (محسنة للكفاءة)
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[logging.StreamHandler()]
)

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
STATE_FILE = "state.json"
AUDIT_LOG = "audit_log.jsonl"
MEDIA_FOLDER = "media/"

# حدود أكثر دقة وكفاءة
MIN_HOURS_BETWEEN_THREADS = int(os.getenv("MIN_HOURS_BETWEEN", "24"))
MAX_REPLIES_PER_RUN = 2
MAX_REPLIES_PER_DAY = 5

ENABLE_MEDIA = True
MEDIA_TYPES = ["infographic_ai.png", "cheat_sheet.png", "quick_tip.mp4"]  # قلل العدد

# نماذج مرتبة حسب السرعة/التكلفة (الأسرع/الأرخص أولاً)
FALLBACK_MODELS = [
    "qwen/qwen-2.5-32b-instruct",           # أسرع وأرخص
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.1-70b-instruct"
]

DEFAULT_HASHTAGS = ["#ذكاء_اصطناعي", "#تقنية"]


class TechExpertMasterFinal:
    """
    نسخة محسنة كفاءة + أمان + نمو:
    - exponential backoff + jitter لـ API calls
    - caching للردود المتكررة
    - تقليل استدعاءات OpenAI
    - تحميل/حفظ حالة أقل تكراراً
    - media فقط عند الحاجة
    """

    def __init__(self):
        self.dry_run = os.getenv("DRY_RUN", "0") == "1"
        self.signature = os.getenv("SIGNATURE", "").strip()

        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        self.client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True
        )

        self.content_pillars = {
            "الذكاء الاصطناعي": "Generative AI, Agents, أخلاقيات",
            "الأمن السيبراني": "Zero Trust, Passkeys, Ransomware",
            "البرمجة": "Python/Rust, AI tools, Clean Code",
            "مبادرات سعودية AI": "سدايا, علّام, كورسات مجانية",
            "مقارنات AI": "Grok vs ChatGPT vs Gemini"
        }

        self.system_instr = (
            "مختص تقني عربي محترف. اكتب بدقة ووضوح.\n"
            "ممنوع اختلاق بيانات/مصادر.\n"
            "هيكل: Hook → Value → سؤال تفاعلي.\n"
            "لا هاشتاقات داخل النص.\n"
            "أنهِ الثريد بسؤال يشجع التفاعل."
        )

        self.state = self._load_state()
        self._replies_today = self._load_daily_reply_count()
        self._last_thread_time = self.state.get("last_thread_time", 0)

        # Cache بسيط لتقليل استدعاءات AI متكررة
        self._reply_cache = {}

    # ───────────────────────────────────────────────
    # مساعدات كفاءة + backoff
    # ───────────────────────────────────────────────

    def _exponential_backoff(max_retries=5, base_delay=1.0):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                delay = base_delay
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except (RateLimitError, tweepy.TooManyRequests) as e:
                        jitter = random.uniform(0, 0.1 * delay)
                        sleep_time = delay + jitter
                        logging.warning(f"Rate limit → wait {sleep_time:.1f}s (attempt {attempt+1})")
                        time.sleep(sleep_time)
                        delay *= 2  # exponential
                raise RuntimeError(f"Max retries ({max_retries}) exceeded")
            return wrapper
        return decorator

    def _load_state(self) -> Dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_mention_id": None, "last_thread_time": 0, "replies_today": 0, "reply_reset": ""}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False)

    def _audit(self, event: str, data: dict = None):
        record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **(data or {})}
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _sleep_jitter(self, min_s=1.5, max_s=12.0):
        time.sleep(min_s + random.random() * (max_s - min_s))

    def _load_daily_reply_count(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        reset = self.state.get("reply_reset", today)
        if reset != today:
            self.state["reply_reset"] = today
            self.state["replies_today"] = 0
            self._save_state()
        return self.state.get("replies_today", 0)

    # ───────────────────────────────────────────────
    # Hashtag + تنظيف (محسن)
    # ───────────────────────────────────────────────

    HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)

    def _extract_hashtags(self, text: str) -> tuple[str, List[str]]:
        tags = ["#" + m.group(1) for m in self.HASHTAG_RE.finditer(text)]
        cleaned = self.HASHTAG_RE.sub("", text).strip()
        return cleaned, tags

    def _apply_hashtags_to_last_tweet(self, tweets: List[str], max_tags: int = 2) -> List[str]:
        all_tags = []
        cleaned = []
        for t in tweets:
            c, tags = self._extract_hashtags(t)
            cleaned.append(c)
            all_tags.extend(tags)

        final_tags = (all_tags or self.DEFAULT_HASHTAGS)[:max_tags]
        tag_line = " ".join(final_tags)

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

    # ───────────────────────────────────────────────
    # توليد المحتوى (مع caching + max_tokens أقل)
    # ───────────────────────────────────────────────

    @_exponential_backoff()
    def _generate_with_model(self, messages: list, model: str, max_tokens: int = 800) -> str:
        resp = self.ai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.65
        )
        return resp.choices[0].message.content.strip()

    def _generate_thread(self, pillar: str, details: str) -> List[str]:
        prompt = (
            f"Thread تقني عربي عن: {pillar} ({details})\n"
            f"افصل بـ: {THREAD_DELIM}\n"
            "- 3–5 تغريدات\n"
            "- 90–260 حرف/تغريدة\n"
            "- Hook → Value → سؤال تفاعلي\n"
            "- لا هاشتاقات\n"
            "- أنهِ بسؤال يشجع الردود"
        )

        messages = [
            {"role": "system", "content": self.system_instr},
            {"role": "user", "content": prompt}
        ]

        for model in FALLBACK_MODELS:
            try:
                raw = self._generate_with_model(messages, model)
                parts = [p.strip() for p in raw.split(THREAD_DELIM) if len(p.strip()) >= 80]
                if 3 <= len(parts) <= 5:
                    return parts
            except Exception as e:
                logging.warning(f"Model {model} failed: {e}")
                time.sleep(2)

        raise RuntimeError("فشل توليد الثريد بعد جميع النماذج")

    def _add_numbering_prefix(self, tweets: List[str]) -> List[str]:
        n = len(tweets)
        if n <= 1:
            return tweets
        return [f"{i}/{n} {t.strip()}" for i, t in enumerate(tweets, 1)]

    # ───────────────────────────────────────────────
    # النشر (مع backoff + media محسن)
    # ───────────────────────────────────────────────

    @_exponential_backoff(max_retries=4, base_delay=2.0)
    def _publish_tweet(self, text: str, reply_to: Optional[str] = None, media_path: Optional[str] = None) -> Dict:
        if self.dry_run:
            logging.info(f"[DRY] {text[:60]}... (media: {media_path})")
            return {"id": f"dry_{random.randint(10000,99999)}"}

        kwargs = {"text": text, "user_auth": True}
        if reply_to:
            kwargs["in_reply_to_tweet_id"] = reply_to

        if media_path and ENABLE_MEDIA:
            full_path = os.path.join(MEDIA_FOLDER, media_path)
            if os.path.exists(full_path):
                media = self.client_v2.media_upload(filename=full_path)
                kwargs["media_ids"] = [media.media_id_string]
            else:
                logging.warning(f"Media not found: {media_path}")

        resp = self.client_v2.create_tweet(**kwargs)
        tid = resp.data["id"]
        self._audit("publish_success", {"id": tid})
        return resp.data

    def _publish_thread(self, tweets: List[str]) -> List[str]:
        ids = []
        prev_id = None

        for i, text in enumerate(tweets):
            if i > 0:
                self._sleep_jitter(6, 20)

            media = None
            if i == 0 and random.random() < 0.4 and ENABLE_MEDIA:
                media = random.choice(MEDIA_TYPES)

            data = self._publish_tweet(text, prev_id, media)
            prev_id = data["id"]
            ids.append(prev_id)

        self.state["last_thread_time"] = time.time()
        self._save_state()
        return ids

    # ───────────────────────────────────────────────
    # الردود (مع cache لتقليل AI calls)
    # ───────────────────────────────────────────────

    def _should_reply(self, text: str) -> bool:
        return bool(re.search(REPLY_PATTERN, text)) and len(text) > 35

    def _generate_reply(self, mention_text: str) -> str:
        cache_key = mention_text[:120]  # cache بسيط
        if cache_key in self._reply_cache:
            return self._reply_cache[cache_key]

        prompt = (
            f"رد تقني مختصر (1–3 جمل) مهذب على:\n{mention_text}\n"
            "لا هاشتاقات. اقترح سؤال تفاعلي إذا أمكن."
        )

        messages = [
            {"role": "system", "content": self.system_instr},
            {"role": "user", "content": prompt}
        ]

        reply = self._generate_with_model(messages, FALLBACK_MODELS[0], max_tokens=140)
        reply = re.sub(r"#\w+", "", reply).strip()[:TWEET_LIMIT - 10]

        self._reply_cache[cache_key] = reply
        return reply

    def _interact(self):
        if self._replies_today >= MAX_REPLIES_PER_DAY:
            return

        me = self.client_v2.get_me(user_auth=True).data
        since_id = self.state.get("last_mention_id")

        mentions = self.client_v2.get_users_mentions(
            id=me.id, since_id=since_id, max_results=5, user_auth=True  # قلل للكفاءة
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
            self._sleep_jitter(8, 25)

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

    # ───────────────────────────────────────────────
    # التشغيل الرئيسي
    # ───────────────────────────────────────────────

    def run(self):
        # التحقق من الثريد
        if (time.time() - self._last_thread_time) / 3600 >= MIN_HOURS_BETWEEN_THREADS:
            pillar, details = random.choice(list(self.content_pillars.items()))
            raw = self._generate_thread(pillar, details)
            if raw:
                numbered = self._add_numbering_prefix(raw)
                final = self._apply_hashtags_to_last_tweet(numbered)
                try:
                    self._publish_thread(final)
                except Exception as e:
                    logging.error(f"Thread failed: {e}")
        else:
            logging.info("مبكر لثريد جديد")

        self._sleep_jitter(4, 15)
        self._interact()

        logging.info("دورة انتهت")


if __name__ == "__main__":
    TechExpertMasterFinal().run()
