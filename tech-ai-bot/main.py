# -*- coding: utf-8 -*-
"""
Tech AI Bot (X) — Production (Root layout)
- Smart Scheduler (Ultra) + Weekly plan + Time slots
- Auto‑Compliance Mode
- Smart Reply Inspector 2.0 + Strict Toxicity Filter
- RSS threads, Tips, Polls, Daily Questions, Trending, Growth Boosters
- Video Threads (v1.1 chunked) + Media Cards (Pillow)
- State & audit written to repo root; logs to ./logs/
"""

from __future__ import annotations

import os
import re
import json
import time
import random
import logging
import logging.handlers
import hashlib
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# مسارات الجذر (تدعم الهيكلة في الصورة 100%)
# =============================================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))     # ← جذر المستودع
ROOT_DIR = THIS_DIR                                       # ← الجذر نفسه
SRC_DIR  = os.path.join(ROOT_DIR, "src")
LOG_DIR  = os.path.join(ROOT_DIR, "logs")
WEB_DIR  = os.path.join(ROOT_DIR, "web")

STATE_FILE = os.path.join(ROOT_DIR, "state.json")
AUDIT_LOG  = os.path.join(ROOT_DIR, "audit_log.jsonl")
LOG_FILE   = os.path.join(LOG_DIR, "bot.log")

# =============================================================================
# إعداد اللوج
# =============================================================================
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _ensure_parent_dir(file_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

def setup_logging():
    _ensure_dir(LOG_DIR)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024,
                                              backupCount=5, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    while root.handlers:
        root.removeHandler(root.handlers[0])
    root.addHandler(ch)
    root.addHandler(fh)

setup_logging()
logger = logging.getLogger(__name__)
logger.info("🚀 Tech AI Bot starting (root layout)…")

# =============================================================================
# ثوابت عامة
# =============================================================================
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"

# خط للبطاقات
CARD_FONT_PATHS = [
    os.path.join(ROOT_DIR, "font.ttf"),
    os.path.join(SRC_DIR,  "font.ttf"),
]

# =============================================================================
# أعلام/إعدادات عبر البيئة
# =============================================================================

# Modes
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
SOURCE_MODE = os.getenv("SOURCE_MODE", "1") == "1"
POLL_MODE   = os.getenv("POLL_MODE", "1") == "1"
TIP_MODE    = os.getenv("TIP_MODE", "1") == "1"
SHOW_DASHBOARD = os.getenv("SHOW_DASHBOARD", "0") == "1"

# Signature
SIGNATURE = os.getenv("SIGNATURE", "").strip()

# Quiet hours & compliance
QUIET_HOURS_UTC = os.getenv("QUIET_HOURS_UTC", "0-5")
AUTO_KILL_ON_ERRORS = os.getenv("AUTO_KILL_ON_ERRORS", "1") == "1"
MAX_ERRORS_PER_RUN  = int(os.getenv("MAX_ERRORS_PER_RUN", "3"))
KILL_COOLDOWN_MINUTES = int(os.getenv("KILL_COOLDOWN_MINUTES", "180"))

# Posting guards
POST_CAP_MONTHLY      = int(os.getenv("POST_CAP_MONTHLY", "3000"))
READ_CAP_MONTHLY      = int(os.getenv("READ_CAP_MONTHLY", "15000"))
POSTS_PER_15MIN_SOFT  = int(os.getenv("POSTS_PER_15MIN_SOFT", "95"))

# Replies
REPLY_ENABLED = os.getenv("REPLY_ENABLED", "1") == "1"
MAX_REPLIES_PER_RUN          = int(os.getenv("MAX_REPLIES_PER_RUN", "2"))
MAX_REPLIES_PER_HOUR         = int(os.getenv("MAX_REPLIES_PER_HOUR", "4"))
MAX_REPLIES_PER_DAY          = int(os.getenv("MAX_REPLIES_PER_DAY", "12"))
MAX_REPLIES_PER_USER_PER_DAY = int(os.getenv("MAX_REPLIES_PER_USER_PER_DAY", "1"))
REPLY_COOLDOWN_HOURS         = int(os.getenv("REPLY_COOLDOWN_HOURS", "12"))
REPLY_JITTER_MIN             = float(os.getenv("REPLY_JITTER_MIN", "2"))
REPLY_JITTER_MAX             = float(os.getenv("REPLY_JITTER_MAX", "6"))

# Smart Scheduling (Ultra)
SCHED_MODE = os.getenv("SCHED_MODE", "ultra")  # 'safe' | 'growth' | 'ultra'
LOCAL_TZ_OFFSET_MINUTES = int(os.getenv("LOCAL_TZ_OFFSET_MINUTES", "240"))  # GMT+4 (عُمان)
SLOTS_DEF = os.getenv(
    "SLOTS_DEF",
    "rss=11-17;tip=19-22;video=12-15;question=15-20;poll=18-21;trending=14-18;booster=16-20"
)
WEEKLY_PLAN = os.getenv(
    "WEEKLY_PLAN",
    "sun=video,rss;mon=rss,tip;tue=question,rss;wed=tip,trending;thu=video,booster;fri=poll,tip;sat=tip,booster"
)
ENGAGEMENT_HIGH_THRESHOLD   = int(os.getenv("ENGAGEMENT_HIGH_THRESHOLD", "4"))
ENGAGEMENT_COOLDOWN_MINUTES = int(os.getenv("ENGAGEMENT_COOLDOWN_MINUTES", "45"))
RANDOM_SKIP_CHANCE          = float(os.getenv("RANDOM_SKIP_CHANCE", "0.25"))

# Auto‑Compliance Mode
COMPLIANCE_MODE_ENABLED          = os.getenv("COMPLIANCE_MODE_ENABLED", "1") == "1"
COMPLIANCE_MAX_POSTS_PER_DAY     = int(os.getenv("COMPLIANCE_MAX_POSTS_PER_DAY", "8"))
COMPLIANCE_MAX_ERRORS_PER_WINDOW = int(os.getenv("COMPLIANCE_MAX_ERRORS_PER_WINDOW", "3"))
COMPLIANCE_WINDOW_MINUTES        = int(os.getenv("COMPLIANCE_WINDOW_MINUTES", "60"))
COMPLIANCE_MIN_INTERVAL_MINUTES  = int(os.getenv("COMPLIANCE_MIN_INTERVAL_MINUTES", "20"))
COMPLIANCE_LOCK_DURATION_MINUTES = int(os.getenv("COMPLIANCE_LOCK_DURATION_MINUTES", "180"))
COMPLIANCE_QUIET_HOURS_EXTENSION = int(os.getenv("COMPLIANCE_QUIET_HOURS_EXTENSION", "2"))
COMPLIANCE_STRICT_MODE           = os.getenv("COMPLIANCE_STRICT_MODE", "1") == "1"

# Smart Reply Inspector 2.0
SMART_REPLY_STRICT   = os.getenv("SMART_REPLY_STRICT", "1") == "1"
SMART_REPLY_SOFT_TONE= os.getenv("SMART_REPLY_SOFT_TONE", "1") == "1"
SMART_REPLY_INTENT   = os.getenv("SMART_REPLY_INTENT", "1") == "1"
NO_REPLY_TO_SELF     = os.getenv("NO_REPLY_TO_SELF", "1") == "1"
NO_REPLY_TO_BOTS     = os.getenv("NO_REPLY_TO_BOTS", "1") == "1"
BOT_KEYWORDS = [kw.strip().lower() for kw in os.getenv(
    "BOT_KEYWORDS", "bot,بوت,automated,automation,🤖"
).split(",") if kw.strip()]

REPLY_MIN_LEN       = int(os.getenv("REPLY_MIN_LEN", "25"))
REPLY_SIM_THRESHOLD = float(os.getenv("REPLY_SIM_THRESHOLD", "0.75"))
REPLY_HASH_WINDOW   = int(os.getenv("REPLY_HASH_WINDOW", "200"))

# Strict Toxicity Filter
TOXIC_STRICT_ENABLED          = os.getenv("TOXIC_STRICT_ENABLED", "1") == "1"
TOXIC_USER_COOLDOWN_HOURS     = int(os.getenv("TOXIC_USER_COOLDOWN_HOURS", "24"))
HOSTILE_USER_COOLDOWN_MINUTES = int(os.getenv("HOSTILE_USER_COOLDOWN_MINUTES", "90"))
TOXIC_SCORE_THRESHOLD         = float(os.getenv("TOXIC_SCORE_THRESHOLD", "0.65"))
HOSTILE_SCORE_THRESHOLD       = float(os.getenv("HOSTILE_SCORE_THRESHOLD", "0.40"))
TOXIC_WINDOW_MINUTES          = int(os.getenv("TOXIC_WINDOW_MINUTES", "60"))
TOXIC_MAX_MATCHES             = int(os.getenv("TOXIC_MAX_MATCHES", "2"))
TOXIC_WHITELIST_TERMS         = [t.strip() for t in os.getenv("TOXIC_WHITELIST_TERMS", "نقد,تصحيح,اقتراح").split(",") if t.strip()]

# X Premium: Pin + Media Cards
PIN_LAST    = os.getenv("PIN_LAST", "1") == "1"
MEDIA_CARDS = os.getenv("MEDIA_CARDS", "1") == "1"
CARD_BRAND  = os.getenv("CARD_BRAND", "Tech AI Bot")

# OpenRouter
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# Video settings
VIDEO_ENABLED          = os.getenv("VIDEO_ENABLED", "1") == "1"
VIDEO_PATH             = os.getenv("VIDEO_PATH", "").strip()
VIDEO_DIR              = os.getenv("VIDEO_DIR", "").strip() or WEB_DIR  # ← افتراضي web/
VIDEO_MAX_MB           = int(os.getenv("VIDEO_MAX_MB", "50"))
VIDEO_MAX_SECONDS      = int(os.getenv("VIDEO_MAX_SECONDS", "75"))
VIDEO_THREAD_ENABLED   = os.getenv("VIDEO_THREAD_ENABLED", "1") == "1"
VIDEO_THREAD_POINTS    = int(os.getenv("VIDEO_THREAD_POINTS", "2"))

# =============================================================================
# RSS & Poll config
# =============================================================================
POLL_EVERY_DAYS      = int(os.getenv("POLL_EVERY_DAYS", "7"))
POLL_DURATION_MINUTES= int(os.getenv("POLL_DURATION_MINUTES", "1440"))

POLL_CONFIG: Dict[str, Dict[str, Any]] = {
    "الذكاء الاصطناعي": {
        "question": "وين تحب نركّز في ثريد AI القادم؟ 🤖",
        "levels": {
            "beginner": {
                "options": ["وش هو AI أصلًا؟", "كيف أبدأ؟", "أفضل أدوات", "أمثلة بسيطة"],
            },
            "intermediate": {
                "options": ["المخرجات غير دقيقة", "الشرح مو واضح", "التكلفة مرتفعة", "تحسين الاستخدام"],
            },
            "advanced": {
                "options": ["RAG بشكل صحيح", "Agents عمليًا", "تقييم المخرجات", "أمان النماذج"],
            },
        },
    },
    "الحوسبة السحابية": {
        "question": "إيش أكثر شيء يرهقك في السحابة؟ ☁️",
        "levels": {
            "beginner": {
                "options": ["وش هي السحابة؟", "أول خدمة أتعلمها", "فرق AWS وAzure", "أمثلة استخدام"],
            },
            "intermediate": {
                "options": ["ارتفاع التكاليف", "التعقيد", "الأمان", "الاعتمادية"],
            },
            "advanced": {
                "options": ["FinOps متقدم", "Zero Trust", "Multi‑Cloud", "SRE عملي"],
            },
        },
    },
    "البرمجة": {
        "question": "إيش أكثر شيء يضيّع وقتك في البرمجة؟ 👨‍💻",
        "levels": {
            "beginner": {
                "options": ["من وين أبدأ؟", "لغة أتعلمها", "أمثلة بسيطة", "أخطاء شائعة"],
            },
            "intermediate": {
                "options": ["Debugging", "اختبارات", "تنظيم الكود", "أداء التطبيق"],
            },
            "advanced": {
                "options": ["Refactoring كبير", "أداء عالي", "أنماط معمارية", "Scalability"],
            },
        },
    },
    "نصائح تقنية يومية": {
        "question": "وش تحب نصيحة اليوم تكون عن؟ 💡",
        "levels": {
            "beginner": {"options": ["AI يومي", "أجهزة ذكية", "مواقع التواصل", "خصوصية وأمان"]},
            "intermediate": {"options": ["AI يومي", "أجهزة ذكية", "مواقع التواصل", "خصوصية وأمان"]},
            "advanced": {"options": ["AI يومي", "أجهزة ذكية", "مواقع التواصل", "خصوصية وأمان"]},
        },
    },
}

FEEDS: Dict[str, List[str]] = {
    "الذكاء الاصطناعي": [
        "https://openai.com/news/rss.xml",
        "https://cloud.google.com/blog/rss",
        "https://blogs.microsoft.com/feed",
    ],
    "الحوسبة السحابية": [
        "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
        "https://cloud.google.com/blog/rss",
    ],
    "البرمجة": [
        "https://devblogs.microsoft.com/dotnet/feed/",
        "https://devblogs.microsoft.com/visualstudio/feed/",
    ],
    "نصائح تقنية يومية": [
        "https://openai.com/news/rss.xml",
        "https://blog.google/rss/",
        "https://android-developers.googleblog.com/atom.xml",
        "https://security.googleblog.com/feeds/posts/default?alt=rss",
        "https://www.apple.com/newsroom/rss-feed.rss",
        "https://about.fb.com/news/feed/",
        "https://instagram-engineering.com/feed",
    ],
}

# =============================================================================
# وظائف مساعدة عامة
# =============================================================================
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def clamp_tweet(text: str) -> str:
    return text if len(text) <= TWEET_LIMIT else (text[: TWEET_LIMIT - 1] + "…")

def sleep_jitter(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

def in_quiet_hours(cfg: str) -> bool:
    try:
        start_h, end_h = [int(x) for x in cfg.split("-", 1)]
        now_h = datetime.now(timezone.utc).hour
        return start_h <= now_h <= end_h
    except Exception:
        return False

def month_key(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m")

def day_key(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")

def append_jsonl(path: str, obj: dict):
    _ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def http_get(url: str, timeout: int = 20) -> Optional[bytes]:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (TechAI Bot)"})
        with urlopen(req, timeout=timeout) as r:
            return r.read()
    except (URLError, HTTPError) as e:
        logger.warning(f"HTTP error for {url}: {e}")
        return None

def parse_rss(url: str) -> List[Dict[str, str]]:
    data = http_get(url)
    if not data:
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    items: List[Dict[str, str]] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "summary": desc})
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = (link_el.get("href") if link_el is not None else "").strip()
        summary = (entry.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "summary": summary})
    return items

# =============================================================================
# OpenRouter (openai 2.x)
# =============================================================================
def call_ai(system_prompt: str, user_prompt: str, model: str = OPENROUTER_MODEL,
            max_tokens: int = 800, temperature: float = 0.7) -> str:
    client = TechBot._ai_client  # type: ignore[attr-defined]
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = resp.choices[0].message.content or ""
        return content.strip()
    except Exception as e:
        logger.error(f"AI error: {e}")
        return ""

def make_thread_from_source(title: str, summary: str, source_url: str, pillar: str) -> List[str]:
    instr = (
        "اكتب كمختص تقني عربي بأسلوب بسيط وودود.\n"
        "كل تغريدة لا تتجاوز 280 حرفًا.\n"
        "التزم: Hook ثم Value ثم CTA (سؤال لطيف).\n"
        "لا تضع هاشتاقات داخل النص.\n"
        "لا تضع روابط داخل النص؛ سنضيف رابط المصدر في آخر تغريدة كسطر مستقل يبدأ بـ 'المصدر:'.\n"
        "اجعل الثريد مباشرًا وواضحًا ومفيدًا للقارئ العربي.\n"
    )
    user = (
        f"المصدر يتحدث عن: «{title}»\n"
        f"ملخص سريع (إن وُجد): {summary or 'لا يوجد'}\n"
        f"المجال/الركيزة: {pillar}\n"
        f"رجاءً أعد صياغة ثريد من 3-5 تغريدات. افصل بين كل تغريدة بسطر يحتوي بالضبط على: {THREAD_DELIM!r}\n"
        "لا تُدرج الرابط ضمن النص."
    )
    text = call_ai(instr, user)
    if not text:
        tweets = [
            f"📌 جديد في {pillar}: {title}",
            "الخلاصة: نقطة مفيدة أو اثنتان من أبرز ما جاء في المصدر.",
            "رأيك؟ هل تهمك هذه الجزئية أم تريد تفاصيل أكثر؟"
        ]
    else:
        tweets = [t.strip() for t in text.split(THREAD_DELIM) if t.strip()]

    if source_url:
        if tweets:
            last = tweets[-1]
            suffix = f"\nالمصدر: {source_url}"
            tweets[-1] = clamp_tweet(last + suffix)
        else:
            tweets = [clamp_tweet(f"المصدر: {source_url}")]

    if SIGNATURE:
        tweets = [clamp_tweet(t + f"\n{SIGNATURE}") for t in tweets]
    return tweets

# =============================================================================
# الكلاس الرئيسي
# =============================================================================
class TechBot:
    _ai_client: OpenAI = None  # type: ignore

    def __init__(self):
        self._require_env()

        # OpenRouter API client
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=os.getenv("OPENROUTER_API_KEY"))
        TechBot._ai_client = self.ai

        # X client (v2)
        self.x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )

        # v1.1 API for media upload
        self._init_api_v1()

        self._me_id: Optional[str] = None
        self.state = self._load_state()
        logger.info("📌 Root layout OK: logs/ , src/ , web/ , state.json , audit_log.jsonl")

    # ----------------------------
    # Env
    # ----------------------------
    def _require_env(self):
        needed = ["OPENROUTER_API_KEY", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing = [k for k in needed if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

    # ----------------------------
    # State & Audit
    # ----------------------------
    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
            except Exception:
                s = {}
        else:
            s = {}

        # Posting guards
        s.setdefault("used_links", [])
        s.setdefault("month_key", None)
        s.setdefault("posts_this_month", 0)
        s.setdefault("reads_this_month", 0)
        s.setdefault("post_times_15m", [])

        # Polls
        s.setdefault("last_poll_at", None)
        s.setdefault("last_poll_id", None)
        s.setdefault("last_poll_pillar", None)
        s.setdefault("last_poll_level", None)
        s.setdefault("last_poll_processed", False)
        s.setdefault("poll_pillar_index", 0)
        s.setdefault("poll_level_index", 0)
        s.setdefault("poll_perf", {})

        # Replies
        s.setdefault("last_mention_id", None)
        s.setdefault("replied_to_ids", [])
        s.setdefault("recent_reply_hashes", [])
        s.setdefault("recent_reply_texts", [])
        s.setdefault("reply_user_cooldown", {})
        s.setdefault("reply_times_1h", [])
        s.setdefault("reply_day_key", None)
        s.setdefault("replies_today", 0)
        s.setdefault("replies_today_by_user", {})
        s.setdefault("user_reply_hashes", {})
        s.setdefault("opt_out_users", [])
        s.setdefault("reply_kill_until", None)
        s.setdefault("errors_last_run", 0)

        # TOD
        s.setdefault("tod_day_key", None)
        s.setdefault("tod_pillar", None)
        s.setdefault("tod_choice", None)
        s.setdefault("tod_keywords", [])
        s.setdefault("tod_poll_id", None)

        # Smart scheduling
        s.setdefault("last_content_type", None)
        s.setdefault("content_counts_today", {})
        s.setdefault("last_counts_day", None)

        # Strict toxicity
        s.setdefault("toxic_user_block_until", {})
        s.setdefault("hostile_user_cooldown_until", {})
        s.setdefault("recent_toxic_hits", [])

        return s

    def _save_state(self):
        _ensure_parent_dir(STATE_FILE)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _audit(self, event_type: str, payload: dict, content_type: str = None):
        append_jsonl(AUDIT_LOG, {
            "ts": utcnow_iso(),
            "type": event_type,
            "content_type": content_type,
            "payload": payload,
        })

    # =============================================================================
    # v1.1 Media API
    # =============================================================================
    def _init_api_v1(self):
        try:
            auth = tweepy.OAuth1UserHandler(
                os.getenv("X_API_KEY"),
                os.getenv("X_API_SECRET"),
                os.getenv("X_ACCESS_TOKEN"),
                os.getenv("X_ACCESS_SECRET"),
            )
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
        except Exception as e:
            self.api_v1 = None
            logger.warning(f"v1.1 media API init failed: {e}")

    def media_upload_image(self, image_path: str) -> Optional[str]:
        if not self.api_v1:
            return None
        try:
            media = self.api_v1.media_upload(filename=image_path)
            return getattr(media, "media_id_string", None)
        except Exception as e:
            logger.warning(f"media upload failed: {e}")
            return None

    # =============================================================================
    # بطاقات صورة
    # =============================================================================
    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for p in CARD_FONT_PATHS:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def build_card_image(self, title: str, body: str, out_path: str, w: int = 1200, h: int = 675):
        try:
            _ensure_parent_dir(out_path)
            bg = Image.new("RGB", (w, h), color=(18, 18, 18))
            draw = ImageDraw.Draw(bg)

            title_font = self._load_font(60)
            body_font  = self._load_font(44)
            brand_font = self._load_font(32)

            margin = 60
            y = margin
            draw.text((margin, y), title, font=title_font, fill=(56, 189, 248))
            y += 90

            def wrap(text, font, max_width):
                words = text.split()
                lines, line = [], ""
                for w_ in words:
                    test = (line + " " + w_).strip()
                    if draw.textlength(test, font=font) <= max_width:
                        line = test
                    else:
                        if line: lines.append(line)
                        line = w_
                if line: lines.append(line)
                return lines

            max_text_width = w - (2 * margin)
            for ln in wrap(body, body_font, max_text_width):
                draw.text((margin, y), ln, font=body_font, fill=(241, 245, 249))
                y += 58

            draw.line((margin, h - 90, w - margin, h - 90), fill=(38, 38, 38), width=2)
            draw.text((margin, h - 70), CARD_BRAND, font=brand_font, fill=(148, 163, 184))

            bg.save(out_path, format="PNG")
            return out_path
        except Exception as e:
            logger.warning(f"Card build failed: {e}")
            return None

    # =============================================================================
    # Twitter primitives
    # =============================================================================
    def me_id(self) -> str:
        if self._me_id:
            return self._me_id
        me = self.x.get_me()
        self._me_id = me.data.id  # type: ignore
        return self._me_id

    def _register_post_event(self, text: str):
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        hist = self.state.get("recent_post_hashes", [])
        hist = (hist + [h])[-50:]
        self.state["recent_post_hashes"] = hist
        pts = self.state.get("recent_post_times", [])
        now_ts = time.time()
        cutoff = now_ts - COMPLIANCE_WINDOW_MINUTES * 60
        pts = [t for t in pts if t >= cutoff] + [now_ts]
        self.state["recent_post_times"] = pts
        self._save_state()

    def _register_error_event(self):
        errs = self.state.get("recent_errors", [])
        now_ts = time.time()
        cutoff = now_ts - COMPLIANCE_WINDOW_MINUTES * 60
        errs = [t for t in errs if t >= cutoff] + [now_ts]
        self.state["recent_errors"] = errs
        self._save_state()
        if COMPLIANCE_MODE_ENABLED and len(errs) >= COMPLIANCE_MAX_ERRORS_PER_WINDOW:
            self._enter_lock("error_window_exceeded")

    def _is_locked(self) -> bool:
        lock_until = self.state.get("compliance_lock_until")
        if not lock_until:
            return False
        try:
            return datetime.now(timezone.utc) < datetime.fromisoformat(lock_until)
        except Exception:
            return False

    def _enter_lock(self, reason: str):
        until = datetime.now(timezone.utc) + timedelta(minutes=COMPLIANCE_LOCK_DURATION_MINUTES)
        self.state["compliance_lock_until"] = until.isoformat()
        self._save_state()
        logger.warning(f"🛑 Compliance lock activated ({reason}) until {until.isoformat()}")
        self._audit("compliance_lock", {"reason": reason, "until": until.isoformat()})
        if COMPLIANCE_STRICT_MODE:
            self._features_soft_off()

    def _features_soft_off(self):
        self._compliance_soft_off = {"video": True, "media_cards": True, "boosters": True, "trending": True}

    def _features_soft_on(self):
        self._compliance_soft_off = {}

    def _is_feature_allowed(self, name: str) -> bool:
        return not getattr(self, "_compliance_soft_off", {}).get(name, False)

    def _should_post_now(self) -> bool:
        if self._is_locked():
            return False
        if in_quiet_hours(QUIET_HOURS_UTC):
            return False
        pts = self.state.get("recent_post_times", [])
        now_ts = time.time()
        cutoff = now_ts - COMPLIANCE_WINDOW_MINUTES * 60
        pts = [t for t in pts if t >= cutoff]
        if pts:
            last = max(pts)
            if now_ts - last < COMPLIANCE_MIN_INTERVAL_MINUTES * 60:
                return False
        return True

    def _maybe_release_lock(self):
        if not self._is_locked():
            self._features_soft_on()

    def post_tweet(self, text: str, reply_to: Optional[str] = None, media_ids: Optional[List[str]] = None) -> Optional[str]:
        text = clamp_tweet(text)

        # Compliance pre-check
        if COMPLIANCE_MODE_ENABLED and not self._should_post_now():
            logger.info("⏸️ Compliance pause: skipping post now.")
            self._audit("compliance_skip", {"reason": "precheck_block", "text": text})
            return None

        if DRY_RUN:
            logger.info(f"[DRY_RUN] Tweet: {text} | media={media_ids} | reply_to={reply_to}")
            self._register_post_event(text)
            return "dryrun-0"

        try:
            if reply_to:
                resp = self.x.create_tweet(
                    text=text,
                    in_reply_to_tweet_id=reply_to,
                    media={"media_ids": media_ids} if media_ids else None
                )
            else:
                resp = self.x.create_tweet(text=text, media={"media_ids": media_ids} if media_ids else None)
            tid = resp.data["id"]  # type: ignore
            logger.info(f"✅ Posted tweet: {tid}")
            self._audit("tweet_posted", {"tweet_id": tid, "reply_to": reply_to, "text": text})
            self._register_post_event(text)
            self._maybe_release_lock()
            return tid
        except Exception as e:
            logger.error(f"❌ Tweet failed: {e}")
            self._audit("tweet_error", {"error": str(e), "text": text})
            self._bump_error()
            self._register_error_event()
            return None

    def post_thread(self, tweets: List[str]) -> Optional[str]:
        if not tweets:
            return None
        first_id = self.post_tweet(tweets[0])
        if not first_id:
            return None
        parent = first_id
        for t in tweets[1:]:
            sleep_jitter(0.8, 1.6)
            new_id = self.post_tweet(t, reply_to=parent)
            if not new_id:
                break
            parent = new_id
        return first_id

    def create_poll(self, question: str, options: List[str], duration_minutes: int) -> Optional[str]:
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Poll: {question} -> {options} ({duration_minutes}m)")
            return "dryrun-poll-0"
        try:
            resp = self.x.create_tweet(
                text=clamp_tweet(question),
                poll={"options": options[:4], "duration_minutes": duration_minutes},
            )
            tid = resp.data["id"]  # type: ignore
            logger.info(f"✅ Created poll tweet: {tid}")
            self._audit("poll_created", {"tweet_id": tid, "question": question, "options": options})
            return tid
        except Exception as e:
            logger.error(f"❌ Poll create failed: {e}")
            self._audit("poll_error", {"error": str(e), "question": question, "options": options})
            self._bump_error()
            return None

    def fetch_poll_winner(self, poll_tweet_id: str) -> Optional[str]:
        try:
            resp = self.x.get_tweet(
                id=poll_tweet_id,
                expansions=["attachments.poll_ids"],
                tweet_fields=["attachments"],
                poll_fields=["options", "voting_status", "end_datetime", "duration_minutes"],
            )
            polls = getattr(resp, "includes", {}).get("polls") if hasattr(resp, "includes") else None  # type: ignore
            if not polls:
                return None
            options = polls[0].get("options", [])
            if not options:
                return None
            winner = max(options, key=lambda o: o.get("votes", 0))
            return winner.get("label")
        except Exception as e:
            logger.warning(f"poll winner fetch failed: {e}")
            return None

    # =============================================================================
    # RSS
    # =============================================================================
    def pick_feed_item(self, pillar: str) -> Optional[Dict[str, str]]:
        sources = FEEDS.get(pillar, [])
        random.shuffle(sources)
        for u in sources:
            items = parse_rss(u)
            for item in items[:5]:
                link = item.get("link", "")
                if not link or link in self.state["used_links"]:
                    continue
                return item
        return None

    def post_from_feed(self):
        pillar = random.choice(["الذكاء الاصطناعي", "الحوسبة السحابية", "البرمجة"])
        item = self.pick_feed_item(pillar)

        if not item:
            logger.info("لا يوجد عنصر مناسب للنشر من RSS — سأستخدم failsafe.")
            if VIDEO_ENABLED and VIDEO_THREAD_ENABLED and self._is_feature_allowed("video"):
                if self.maybe_post_video_thread_from_topic("💡 نصيحة تقنية", title="💡 نصيحة تقنية"):
                    return
            self.post_failsafe_tip()
            return

        title  = item["title"]
        link   = item["link"]
        summary= item.get("summary") or ""
        tweets = make_thread_from_source(title, summary, link, pillar)
        tid = self.post_thread(tweets)
        if tid:
            self.state["used_links"].append(link)
            self._save_state()

    # =============================================================================
    # Failsafe tip
    # =============================================================================
    def _pick_failsafe_domain(self) -> Tuple[str, str]:
        choices = ["smart_devices", "ai"]
        key = random.choice(choices)
        return (key, "الأجهزة الذكية") if key == "smart_devices" else (key, "الذكاء الاصطناعي وتطبيقاته")

    def post_failsafe_tip(self):
        key, domain_text = self._pick_failsafe_domain()

        # جرّب ثريد فيديو أولًا
        if VIDEO_ENABLED and VIDEO_THREAD_ENABLED and self._is_feature_allowed("video"):
            if self.maybe_post_video_thread_from_topic(domain_text, title="💡 نصيحة تقنية"):
                return

        sys = (
            "اكتب نصيحة تقنية متخصصة قصيرة وواضحة جدًا بالعربية، لا تتجاوز 280 حرفًا. "
            "خاطِب القارئ بود واحترام، وقدّم قيمة مباشرة وحيلة عملية. "
            "تجنّب الهاشتاقات والروابط داخل النص. اختم بسؤال صغير لطيف (CTA)."
        )
        user = f"المجال: {domain_text}\nالمطلوب: نصيحة مفيدة عملية اليوم."
        tip = call_ai(sys, user, max_tokens=220, temperature=0.85) or \
              f"نصيحة اليوم في {domain_text}: ركّز على أبسط حيلة تضيف قيمة الآن. ما الحيلة التي تنصح بها؟"

        media_ids = None
        if MEDIA_CARDS and self._is_feature_allowed("media_cards"):
            img_path = os.path.join(LOG_DIR, f"card_tip_{int(time.time())}.png")
            if self.build_card_image("💡 نصيحة تقنية", tip, img_path):
                mid = self.media_upload_image(img_path)
                media_ids = [mid] if mid else None

        if SIGNATURE:
            tip = clamp_tweet(tip + f"\n{SIGNATURE}")

        tid = self.post_tweet(tip, media_ids=media_ids)
        if tid and PIN_LAST:
            self._try_pin_tweet(tid)
        if tid:
            self._audit("failsafe_tip_posted", {"pillar_key": key, "domain": domain_text, "tweet_id": tid})

    # =============================================================================
    # Growth / Question / Trending
    # =============================================================================
    def post_growth_booster(self):
        if not self._is_feature_allowed("boosters"):
            logger.info("Compliance: boosters disabled during lock.")
            return
        # جرّب ثريد فيديو أولًا
        if self.maybe_post_video_thread_from_topic("منشور تعزيز نمو (Booster)", title="💡 فكرة سريعة"):
            return

        sys = ("أنت خبير محتوى. اكتب تغريدة قصيرة مؤثرة وواضحة لا تتجاوز 240 حرفًا، بدون هاشتاقات وبدون روابط، "
               "وتنتهي بسؤال بسيط لتحفيز الردود.")
        user = random.choice([
            "اكتب تغريدة عربية تساعد على زيادة التفاعل وتنتهي بسؤال مباشر.",
            "اكتب نصيحة تقنية قصيرة ومؤثرة تشجع على إعادة التغريد، مع سؤال ختامي.",
            "اكتب حيلة تقنية متقدمة بصياغة بسيطة، مع نهاية تفاعلية (CTA)."
        ])
        text = call_ai(sys, user, max_tokens=200, temperature=0.85) or \
               "نصيحة تقنية سريعة: ركّز على أبسط حل أولًا، وحسّن لاحقًا. ما أكثر شيء بسّط عملك مؤخرًا؟"

        media_ids = None
        if MEDIA_CARDS and self._is_feature_allowed("media_cards"):
            img_path = os.path.join(LOG_DIR, f"card_booster_{int(time.time())}.png")
            body = text.replace(SIGNATURE, "").strip() if SIGNATURE else text
            if self.build_card_image("💡 فكرة سريعة", body, img_path):
                mid = self.media_upload_image(img_path)
                media_ids = [mid] if mid else None

        if SIGNATURE:
            text = clamp_tweet(text + f"\n{SIGNATURE}")

        tid = self.post_tweet(text, media_ids=media_ids)
        if tid and PIN_LAST: self._try_pin_tweet(tid)
        if tid: self._audit("growth_booster_posted", {"tweet_id": tid})

    def post_daily_question(self):
        q = random.choice([
            "وش أقوى خدعة تقنية تعلمتها غيرت شغلك؟",
            "لو عندك نصيحة واحدة فقط لمطور جديد، وش بتكون؟",
            "أفضل جهاز ذكي استخدمته خلال آخر سنة؟ وليش؟",
            "وش أكثر ميزة تتمنى تشوفها في ذكاء اصطناعي يوميًا؟"
        ])
        if self.maybe_post_video_thread_from_topic(q, title="❓ سؤال اليوم"):
            return

        text = f"❓ {q}"
        media_ids = None
        if MEDIA_CARDS and self._is_feature_allowed("media_cards"):
            img_path = os.path.join(LOG_DIR, f"card_question_{int(time.time())}.png")
            if self.build_card_image("سؤال اليوم", q, img_path):
                mid = self.media_upload_image(img_path)
                media_ids = [mid] if mid else None

        if SIGNATURE:
            text = clamp_tweet(text + f"\n{SIGNATURE}")

        tid = self.post_tweet(text, media_ids=media_ids)
        if tid and PIN_LAST: self._try_pin_tweet(tid)
        if tid: self._audit("daily_question_posted", {"tweet_id": tid})

    def post_trending_snippet(self):
        if not self._is_feature_allowed("trending"):
            logger.info("Compliance: trending disabled during lock.")
            return

        if self.maybe_post_video_thread_from_topic("⚡ ترند تقني"):
            return

        sys = ("اكتب تغريدة عربية قصيرة تشرح نقطة تقنية عن الذكاء الاصطناعي أو الأجهزة الذكية بشكل واضح جدًا، "
               "واجعلها مرتبطة بتوجهات المستخدمين الحالية. بدون روابط أو هاشتاقات. اختم بسؤال بسيط.")
        user= "اختر موضوعًا تقنيًا رائجًا هذه الأيام بين المستخدمين العرب."
        text= call_ai(sys, user, max_tokens=200, temperature=0.75) or \
              "اتجاه ملحوظ: مزج الذكاء الاصطناعي مع المهام اليومية صار أكثر بساطة. ما التطبيق الذي غيّر يومك فعلًا؟"

        media_ids = None
        if MEDIA_CARDS and self._is_feature_allowed("media_cards"):
            img_path = os.path.join(LOG_DIR, f"card_trending_{int(time.time())}.png")
            if self.build_card_image("⚡ ترند تقني", text, img_path):
                mid = self.media_upload_image(img_path)
                media_ids = [mid] if mid else None

        if SIGNATURE:
            text = clamp_tweet(text + f"\n{SIGNATURE}")

        tid = self.post_tweet(text, media_ids=media_ids)
        if tid and PIN_LAST: self._try_pin_tweet(tid)
        if tid: self._audit("trending_snippet_posted", {"tweet_id": tid})

    # =============================================================================
    # فيديو: probe + pick + upload + video thread
    # =============================================================================
    def probe_video_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate,duration",
                "-of", "json", path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                return None
            data = json.loads(res.stdout or "{}")
            streams = data.get("streams", [])
            return streams[0] if streams else None
        except Exception:
            return None

    def _pick_video_clip(self) -> Optional[str]:
        # ملف محدد؟
        if VIDEO_PATH:
            p = VIDEO_PATH if os.path.isabs(VIDEO_PATH) else os.path.join(ROOT_DIR, VIDEO_PATH)
            if os.path.exists(p) and p.lower().endswith((".mp4",".mov",".m4v")):
                size_mb = os.path.getsize(p) / (1024 * 1024)
                if size_mb <= VIDEO_MAX_MB:
                    meta = self.probe_video_metadata(p)
                    if meta:
                        try:
                            dur = float(meta.get("duration", 0))
                            if dur and dur > VIDEO_MAX_SECONDS:
                                return None
                        except Exception:
                            pass
                    return p
            return None

        base = VIDEO_DIR if os.path.isabs(VIDEO_DIR) else os.path.join(ROOT_DIR, VIDEO_DIR)
        if not os.path.isdir(base):
            return None
        candidates = []
        for name in os.listdir(base):
            if name.lower().endswith((".mp4",".mov",".m4v")):
                full = os.path.join(base, name)
                try:
                    size_mb = os.path.getsize(full) / (1024 * 1024)
                except OSError:
                    continue
                if size_mb <= VIDEO_MAX_MB:
                    meta = self.probe_video_metadata(full)
                    if meta:
                        try:
                            dur = float(meta.get("duration", 0))
                            if dur and dur > VIDEO_MAX_SECONDS:
                                continue
                        except Exception:
                            pass
                    candidates.append(full)
        if not candidates:
            return None
        random.shuffle(candidates)
        return candidates[0]

    def media_upload_video(self, video_path: str) -> Optional[str]:
        if not self.api_v1 or not os.path.exists(video_path):
            return None
        try:
            media = self.api_v1.media_upload(
                filename=video_path,
                chunked=True,
                media_category="tweet_video",
            )
            mid = getattr(media, "media_id_string", None)
            return mid
        except Exception as e:
            logger.warning(f"media upload (video) failed: {e}")
            return None

    def add_part_labels(self, texts: List[str]) -> List[str]:
        # ترقيم الأجزاء
        if len(texts) <= 1:
            return [clamp_tweet(t) for t in texts]
        n = len(texts)
        out = []
        for i, t in enumerate(texts, 1):
            label = f"الجزء {i}/{n}"
            out.append(clamp_tweet(f"{label} — {t}"))
        return out

    def generate_thread_points(self, topic: str, count: int) -> List[str]:
        sys = ("اكتب نقاطًا تقنية عربية قصيرة جدًا وواضحة، كل نقطة <= 220 حرفًا، بدون هاشتاقات أو روابط. "
               "أرجِعها مفصولة بثلاث شرطات عمودية |||.")
        user = f"الموضوع: {topic}\nعدد النقاط: {count}"
        text = call_ai(sys, user, max_tokens=300, temperature=0.7)
        if not text:
            return [f"نقطة موجزة عن {topic}", "سؤال بسيط لتحفيز النقاش"]
        points = [ln.strip() for ln in text.split("|||") if ln.strip()]
        points = points[:max(1, count)]
        return [clamp_tweet(p) for p in points]

    def post_video_thread(self, clip_path: str, title: str, points: List[str]) -> Optional[str]:
        mid = self.media_upload_video(clip_path)
        if not mid:
            return None

        first_text = clamp_tweet(title or "🎬 لقطة تقنية قصيرة")
        if SIGNATURE:
            first_text = clamp_tweet(first_text + f"\n{SIGNATURE}")

        first_id = self.post_tweet(first_text, media_ids=[mid])
        if not first_id:
            return None

        labeled = self.add_part_labels(points)
        parent = first_id
        for t in labeled:
            sleep_jitter(0.8, 1.6)
            rid = self.post_tweet(t, reply_to=parent)
            if not rid:
                break
            parent = rid

        if PIN_LAST:
            self._try_pin_tweet(first_id)

        self._audit("video_thread_posted", {"tweet_id": first_id, "points": labeled})
        logger.info(f"🎬 Video thread posted: {first_id}")
        return first_id

    def maybe_post_video_thread_from_topic(self, topic_text: str, title: Optional[str] = None) -> bool:
        if not (VIDEO_ENABLED and VIDEO_THREAD_ENABLED and self._is_feature_allowed("video")):
            return False
        clip = self._pick_video_clip()
        if not clip:
            return False
        points = self.generate_thread_points(topic_text, max(1, VIDEO_THREAD_POINTS))
        title = title or f"🎬 {topic_text}"
        vid_id = self.post_video_thread(clip, title, points)
        return vid_id is not None

    # =============================================================================
    # Pin tweet
    # =============================================================================
    def _try_pin_tweet(self, tweet_id: str):
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Pin tweet: {tweet_id}")
            return
        if not PIN_LAST:
            return
        try:
            self.x.pin_tweet(tweet_id)  # قد لا تكون متاحة في كل الحسابات/الأذونات
            logger.info(f"📌 Pinned tweet: {tweet_id}")
            self._audit("tweet_pinned", {"tweet_id": tweet_id})
        except Exception as e:
            logger.warning(f"Pin not supported or failed: {e}")
            self._audit("tweet_pin_failed", {"tweet_id": tweet_id, "error": str(e)})

    # =============================================================================
    # Smart Reply Inspector 2.0 + Strict Toxicity
    # =============================================================================
    def _normalize(self, s: str) -> str:
        s = s.strip().lower()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[^\w\u0600-\u06FF\s]+", "", s)
        return s

    def _token_set(self, s: str) -> set:
        return set(self._normalize(s).split())

    def _jaccard(self, a: str, b: str) -> float:
        A, B = self._token_set(a), self._token_set(b)
        if not A or not B:
            return 0.0
        inter = len(A & B)
        union = len(A | B)
        return inter / union

    def _looks_like_bot(self, user_obj: dict) -> bool:
        if not NO_REPLY_TO_BOTS:
            return False
        uname = (user_obj.get("username") or "").lower()
        desc  = (user_obj.get("description") or "").lower()
        text  = f"{uname} {desc}"
        return any(kw in text for kw in BOT_KEYWORDS)

    def _soft_rewrite(self, reply: str) -> str:
        if not SMART_REPLY_SOFT_TONE:
            return reply
        sys = ("أعد صياغة الرد التالي بلغة عربية ودودة ومحترمة وواضحة، "
               "بدون وعود مبالغ فيها، واختم بسؤال صغير إن أمكن، لا تتجاوز 280 حرفًا.")
        new_reply = call_ai(sys, reply, max_tokens=180, temperature=0.7)
        return new_reply or reply

    def _classify_intent(self, user_text: str) -> str:
        if not SMART_REPLY_INTENT:
            return "other"
        sys = ("اقرأ النص وحدد نية المستخدم بكلمة واحدة من: "
               "question, help, praise, criticism, bug, other. لا تضف شرحًا.")
        lab = call_ai(sys, user_text, max_tokens=5, temperature=0)
        lab = (lab or "other").strip().lower()
        return lab if lab in {"question","help","praise","criticism","bug","other"} else "other"

    def _craft_by_intent(self, intent: str, base_reply: str, screen: str) -> str:
        if intent == "question":
            return f"{base_reply}\nهل تريد مثال سريع أو توضيح خطوة بخطوة؟"
        if intent == "help":
            return f"{base_reply}\nارفِق تفاصيل أكثر (النظام/الخطوات/الرسالة) أساعدك بدقة."
        if intent == "praise":
            return f"{base_reply}\nممتن لك يا {screen}! إذا عندك اقتراح لتحسين المحتوى، اكتبه."
        if intent == "criticism":
            return f"{base_reply}\nملاحظتك محل تقدير. وش التغيير الذي تتمنى تشوفه؟"
        if intent == "bug":
            return f"{base_reply}\nأرسل الخطأ بالضبط + السياق التقني عشان نحلّه أسرع."
        return base_reply

    # --- Strict toxicity structures ---
    def _now(self) -> datetime: return datetime.now(timezone.utc)

    def _in_future(self, iso_ts: Optional[str]) -> bool:
        if not iso_ts: return False
        try: return self._now() < datetime.fromisoformat(iso_ts)
        except Exception: return False

    def _mark_toxic(self, author_id: str, score: float, text: str):
        block_until = self._now() + timedelta(hours=TOXIC_USER_COOLDOWN_HOURS)
        block_map = self.state.get("toxic_user_block_until", {})
        block_map[str(author_id)] = block_until.isoformat()
        self.state["toxic_user_block_until"] = block_map

        hits = self.state.get("recent_toxic_hits", [])
        hits.append((self._now().timestamp(), str(author_id), score, text[:280]))
        cutoff = self._now().timestamp() - TOXIC_WINDOW_MINUTES * 60
        hits = [h for h in hits if h[0] >= cutoff]
        self.state["recent_toxic_hits"] = hits
        self._save_state()

        self._audit("toxicity_block", {"author_id": str(author_id), "score": score, "until": block_until.isoformat(), "text": text[:280]})

    def _mark_hostile_cooldown(self, author_id: str):
        cool_until = self._now() + timedelta(minutes=HOSTILE_USER_COOLDOWN_MINUTES)
        cool_map = self.state.get("hostile_user_cooldown_until", {})
        cool_map[str(author_id)] = cool_until.isoformat()
        self.state["hostile_user_cooldown_until"] = cool_map
        self._save_state()
        self._audit("hostile_cooldown", {"author_id": str(author_id), "until": cool_until.isoformat()})

    def _is_author_toxic_blocked(self, author_id: str) -> bool:
        return self._in_future(self.state.get("toxic_user_block_until", {}).get(str(author_id)))

    def _is_author_hostile_cooldown(self, author_id: str) -> bool:
        return self._in_future(self.state.get("hostile_user_cooldown_until", {}).get(str(author_id)))

    def detect_toxicity_strict(self, text: str) -> Tuple[str, float]:
        if not TOXIC_STRICT_ENABLED:
            return ("neutral", 0.0)
        t = text.lower()
        toxic_kw = {"غبي","تافه","جاهل","قذر","حقير","انقلع","يا عديم","سخيف","أحمق","خرا","قرف",
                    "stupid","idiot","moron","trash","garbage","fuck","shit","loser","nonsense","ugly"}
        hostile_kw = {"ما تفهم","تعرف شيء","تعليقك غلط","هراء","غير صحيح","فاشل","لا قيمة","تضلل",
                      "you don’t understand","wrong","nobody cares","nonsense","misleading"}
        toxic_hits = sum(1 for w in toxic_kw if w in t)
        hostile_hits = sum(1 for w in hostile_kw if w in t)

        patterns_toxic = [r"\b(يا )?(غ(ب|بّي)|تافه|حقير|مقرف|منحط)\b", r"\b(يلعن|لعنة|قرف)\b", r"(.*)(اقطع)(.*)"]
        pattern_toxic_hits = sum(1 for p in patterns_toxic if re.search(p, t))

        patterns_hostile = [r"\b(تحليلك|رأيك)\s+(غلط|خطأ|هراء)\b",
                            r"\b(لا|مو)?\s*(تفهم|تعرف)\b",
                            r"\b(تضلل|مضلل|غير)\s+(دقيق|صحيح)\b"]
        pattern_hostile_hits = sum(1 for p in patterns_hostile if re.search(p, t))

        neg_markers = {"ولا تفيد","لا معنى","لا قيمة","غير مفيد","سخيف جدًا"}
        neg_hits = sum(1 for w in neg_markers if w in t)

        if any(w in t for w in (TOXIC_WHITELIST_TERMS or [])):
            toxic_hits   = max(0, toxic_hits - 1)
            hostile_hits = max(0, hostile_hits - 1)

        score = (0.5 * min(1.0, toxic_hits / TOXIC_MAX_MATCHES) +
                 0.3 * min(1.0, pattern_toxic_hits / TOXIC_MAX_MATCHES) +
                 0.2 * min(1.0, (hostile_hits + pattern_hostile_hits + neg_hits) / (TOXIC_MAX_MATCHES + 1)))

        if toxic_hits >= TOXIC_MAX_MATCHES or pattern_toxic_hits >= TOXIC_MAX_MATCHES or score >= TOXIC_SCORE_THRESHOLD:
            return ("toxic", score)

        hostile_score = (0.35 * min(1.0, hostile_hits / (TOXIC_MAX_MATCHES + 1)) +
                         0.35 * min(1.0, pattern_hostile_hits / (TOXIC_MAX_MATCHES + 1)) +
                         0.30 * min(1.0, neg_hits / (TOXIC_MAX_MATCHES + 1)))
        if hostile_score >= HOSTILE_SCORE_THRESHOLD:
            return ("hostile", hostile_score)
        return ("neutral", max(score, hostile_score))

    def craft_professional_response(self, context: str) -> str:
        sys = ("أعد صياغة رد قصير جدًا (أقل من 200 حرف)، "
               "بلغـة عربية احترافية ومحايدة، بدون صدام، "
               "بدون اعتذار مبالغ فيه، وبدون هجوم مضاد، "
               "قدّم احترامًا بسيطًا، وركّز على تهدئة الحوار. "
               "اختم بسؤال هادئ إذا كان مناسبًا.")
        return call_ai(sys, context, max_tokens=180, temperature=0.4)

    def inspect_reply(self, user_key: str, user_screen: str, original_text: str, draft_reply: str) -> Optional[str]:
        reply = (draft_reply or "").strip()
        if len(reply) < REPLY_MIN_LEN:
            reply = f"{reply}\nممكن توضح أكثر عشان أساعدك بشكل أفضل؟"

        recent_texts = self.state.get("recent_reply_texts", [])[-REPLY_HASH_WINDOW:]
        for old in recent_texts[-20:]:
            sim = self._jaccard(reply, old)
            if sim >= REPLY_SIM_THRESHOLD:
                sys = ("أعد صياغة الرد التالي بأسلوب مختلف واضح ومفيد، لا يتجاوز 240 حرفًا، "
                       "وتجنّب التكرار اللفظي، اختم بسؤال بسيط.")
                alt = call_ai(sys, reply, max_tokens=200, temperature=0.9)
                reply = alt.strip() if alt else reply
                break

        user_map = self.state.get("user_reply_hashes", {})
        user_set = set(user_map.get(user_key, []))
        h = hashlib.sha256(self._normalize(reply).encode("utf-8")).hexdigest()[:16]
        if h in user_set:
            sys = "اختصر هذا الرد بنقطة جديدة مختلفة مفيدة، وختمه بسؤال بسيط، لا تتجاوز 220 حرفًا."
            alt = call_ai(sys, reply, max_tokens=180, temperature=0.85)
            alt = alt.strip() if alt else ""
            if not alt:
                return None
            reply = alt
            h = hashlib.sha256(self._normalize(reply).encode("utf-8")).hexdigest()[:16]

        reply = self._soft_rewrite(reply)
        intent= self._classify_intent(original_text)
        reply = self._craft_by_intent(intent, reply, user_screen)

        recent_texts = (recent_texts + [reply])[-REPLY_HASH_WINDOW:]
        self.state["recent_reply_texts"] = recent_texts
        user_set.add(h)
        user_map[user_key] = list(user_set)
        self.state["user_reply_hashes"] = user_map
        self._save_state()

        return clamp_tweet(reply)

    # =============================================================================
    # Mentions processing
    # =============================================================================
    def process_mentions(self):
        if not REPLY_ENABLED:
            return

        today = day_key()
        if self.state["reply_day_key"] != today:
            self.state["reply_day_key"] = today
            self.state["replies_today"] = 0
            self.state["replies_today_by_user"] = {}

        if self.state["replies_today"] >= MAX_REPLIES_PER_DAY:
            logger.info("وصلت حد الردود اليومي.")
            return

        now = datetime.now(timezone.utc).timestamp()
        one_hour_ago = now - 3600
        self.state["reply_times_1h"] = [t for t in self.state["reply_times_1h"] if t >= one_hour_ago]
        if len(self.state["reply_times_1h"]) >= MAX_REPLIES_PER_HOUR:
            logger.info("وصلت حد الردود في الساعة الماضية.")
            return

        since_id = self.state.get("last_mention_id")
        try:
            resp = self.x.get_users_mentions(
                id=self.me_id(),
                since_id=since_id,
                max_results=50,
                expansions=["author_id", "in_reply_to_user_id"],
                tweet_fields=["created_at", "in_reply_to_user_id"],
                user_fields=["username", "name", "description"],
            )
        except Exception as e:
            logger.error(f"mentions fetch failed: {e}")
            self._bump_error()
            return

        if not getattr(resp, "data", None):
            logger.info("لا يوجد منشنات جديدة.")
            return

        mentions = sorted(resp.data, key=lambda t: t.id)  # type: ignore
        processed = 0
        me_id = self.me_id()

        for m in mentions:
            if processed >= MAX_REPLIES_PER_RUN:
                break

            tweet_id = m.id  # type: ignore
            author_id = m.author_id  # type: ignore
            text = m.text or ""

            # منع الرد على النفس
            if NO_REPLY_TO_SELF and str(author_id) == str(me_id):
                continue

            # معلومات المستخدم
            user_obj = None
            screen = ""
            if getattr(resp, "includes", None) and "users" in resp.includes:  # type: ignore
                for u in resp.includes["users"]:  # type: ignore
                    if u["id"] == author_id:
                        user_obj = u
                        screen = f"@{u.get('username')}"
                        break

            # منع الرد على حسابات البوت
            if user_obj and self._looks_like_bot(user_obj):
                logger.info(f"⛔ Skipping bot-like account: {screen}")
                continue

            # حظر/تبريد صارم مسبقًا؟
            if self._is_author_toxic_blocked(author_id):
                logger.info(f"🚫 Toxic-block active for {screen}")
                continue
            if self._is_author_hostile_cooldown(author_id):
                logger.info(f"⏸️ Hostile-cooldown active for {screen}")
                continue

            if tweet_id in self.state["replied_to_ids"]:
                continue

            cooldown_map = self.state.get("reply_user_cooldown", {})
            user_rec = cooldown_map.get(str(author_id), {"ts": 0})
            if time.time() - user_rec["ts"] < REPLY_COOLDOWN_HOURS * 3600:
                continue

            # تصنيف صارم للإساءة
            label, tox_score = self.detect_toxicity_strict(text)
            if label == "toxic":
                self._mark_toxic(author_id, tox_score, text)
                logger.info(f"🚫 Toxic mention — blocking replies for {screen}")
                continue
            elif label == "hostile":
                self._mark_hostile_cooldown(author_id)
                context = f"منشن عدواني من {screen}: {text}\n—\nاكتب ردًا احترافيًا غير صدامي وقصير."
                safe_reply = self.craft_professional_response(context)
                final_reply = self.inspect_reply(user_key=str(author_id), user_screen=screen, original_text=text, draft_reply=safe_reply)
                if not final_reply:
                    continue
                sleep_jitter(REPLY_JITTER_MIN, REPLY_JITTER_MAX)
                rid = self.post_tweet(final_reply, reply_to=str(tweet_id))
                if not rid:
                    continue
                # سجل
                self.state["replied_to_ids"].append(tweet_id)
                cooldown_map[str(author_id)] = {"ts": time.time()}
                self.state["reply_user_cooldown"] = cooldown_map
                self.state["last_mention_id"] = max(self.state.get("last_mention_id") or 0, tweet_id)
                self.state["replies_today"] += 1
                self.state["reply_times_1h"].append(time.time())
                self._save_state()
                processed += 1
                continue

            # neutral → الرد الذكي المعتاد
            prompt_sys = (
                "أنت مساعد تقني عربي، ودود، يرد باحترام ووضوح في تغريدة واحدة لا تتجاوز 280 حرفًا. "
                "تجنب الوعود المبالغ فيها والروابط. اختم بسؤال صغير لطيف إن أمكن."
            )
            prompt_user = f"سياق المنشن من {screen}:\n{text}\n—\nاكتب ردًا مناسبًا موجزًا."
            draft = call_ai(prompt_sys, prompt_user, max_tokens=200, temperature=0.7)

            final_reply = self.inspect_reply(user_key=str(author_id), user_screen=screen, original_text=text, draft_reply=draft)
            if not final_reply:
                continue

            sleep_jitter(REPLY_JITTER_MIN, REPLY_JITTER_MAX)
            rid = self.post_tweet(final_reply, reply_to=str(tweet_id))
            if not rid:
                continue

            self.state["replied_to_ids"].append(tweet_id)
            cooldown_map[str(author_id)] = {"ts": time.time()}
            self.state["reply_user_cooldown"] = cooldown_map
            self.state["last_mention_id"] = max(self.state.get("last_mention_id") or 0, tweet_id)
            self.state["replies_today"] += 1
            self.state["reply_times_1h"].append(time.time())
            self._save_state()
            processed += 1

    # =============================================================================
    # Smart Scheduler (Ultra)
    # =============================================================================
    def _local_now(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=LOCAL_TZ_OFFSET_MINUTES)

    def _local_hour(self) -> int:
        return self._local_now().hour

    def _parse_slots(self) -> Dict[str, Tuple[int, int]]:
        slots: Dict[str, Tuple[int, int]] = {}
        for part in SLOTS_DEF.split(";"):
            part = part.strip()
            if not part or "=" not in part or "-" not in part:
                continue
            typ, rng = part.split("=", 1)
            start, end = rng.split("-", 1)
            try:
                slots[typ.strip()] = (int(start), int(end))
            except ValueError:
                continue
        return slots

    def _is_in_slot(self, content_type: str) -> bool:
        slots = getattr(self, "_slots_cache", None)
        if slots is None:
            slots = self._parse_slots()
            self._slots_cache = slots
        rng = slots.get(content_type)
        if not rng:
            return True
        h = self._local_hour()
        return rng[0] <= h <= rng[1]

    def _weekly_plan_for_today(self) -> List[str]:
        day_map = {0:"mon",1:"tue",2:"wed",3:"thu",4:"fri",5:"sat",6:"sun"}
        today = day_map[self._local_now().weekday()]
        plan: Dict[str, List[str]] = {}
        for p in WEEKLY_PLAN.split(";"):
            p = p.strip()
            if not p or "=" not in p:
                continue
            d, lst = p.split("=", 1)
            plan[d.lower().strip()] = [x.strip() for x in lst.split(",") if x.strip()]
        return plan.get(today, ["rss","tip","video","question","trending","booster","poll"])

    def _is_engagement_high(self) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        one_hour_ago = now - 3600
        recent = [t for t in self.state.get("reply_times_1h", []) if t >= one_hour_ago]
        return len(recent) >= ENGAGEMENT_HIGH_THRESHOLD

    def _content_rotation_ok(self, next_type: str) -> bool:
        last = self.state.get("last_content_type")
        return not last or last != next_type

    def _respect_randomization(self) -> bool:
        return random.random() >= RANDOM_SKIP_CHANCE

    def _increment_content_count(self, typ: str):
        today = day_key()
        if self.state.get("last_counts_day") != today:
            self.state["content_counts_today"] = {}
            self.state["last_counts_day"] = today
        counts = self.state.get("content_counts_today", {})
        counts[typ] = counts.get(typ, 0) + 1
        self.state["content_counts_today"] = counts
        self._save_state()

    def _choose_next_action(self) -> Optional[str]:
        if COMPLIANCE_MODE_ENABLED and self._is_locked():
            for ct in ["question","tip"]:
                if self._is_in_slot(ct) and self._respect_randomization():
                    return ct
            return None

        if self._is_engagement_high():
            for ct in ["question","tip"]:
                if self._is_in_slot(ct) and self._content_rotation_ok(ct) and self._respect_randomization():
                    return ct
            return None

        plan = self._weekly_plan_for_today()
        ordered_candidates: List[str] = []
        for ct in plan:
            if ct == "video" and not self._is_feature_allowed("video"):
                continue
            if ct == "booster" and not self._is_feature_allowed("boosters"):
                continue
            if ct == "trending" and not self._is_feature_allowed("trending"):
                continue
            if self._is_in_slot(ct) and self._content_rotation_ok(ct):
                ordered_candidates.append(ct)

        if not ordered_candidates:
            ordered_candidates = [t for t in ["tip","question","rss","trending","booster","poll","video"]
                                  if self._is_in_slot(t)]

        for ct in ordered_candidates:
            if self._respect_randomization():
                return ct
        return ordered_candidates[0] if ordered_candidates else None

    def _execute_action(self, action: str) -> bool:
        before_used_links = len(self.state.get("used_links", []))
        before_tod = self.state.get("tod_day_key")

        if action == "rss":
            self.post_from_feed()
            posted = len(self.state.get("used_links", [])) != before_used_links
        elif action == "tip":
            self.maybe_post_tod()
            posted = self.state.get("tod_day_key") != before_tod
        elif action == "question":
            self.post_daily_question(); posted = True
        elif action == "video":
            self.post_trending_snippet(); posted = True
        elif action == "trending":
            self.post_trending_snippet(); posted = True
        elif action == "booster":
            self.post_growth_booster(); posted = True
        elif action == "poll":
            last_poll = self.state.get("last_poll_at")
            self.maybe_post_poll()
            posted = self.state.get("last_poll_at") != last_poll
        else:
            posted = False

        if posted:
            self.state["last_content_type"] = action
            self._increment_content_count(action)
            self._save_state()
        return posted

    def do_scheduled_post(self) -> bool:
        action = self._choose_next_action()
        if not action:
            logger.info("SmartScheduler: لا يوجد فعل مناسب للنشر الآن.")
            return False
        logger.info(f"SmartScheduler: محاولة نشر فعل '{action}'")
        posted = self._execute_action(action)
        if not posted and SOURCE_MODE and FAILSAFE_ENABLED:
            logger.info("SmartScheduler: لم يتم النشر—سأحاول failsafe tip.")
            self.post_failsafe_tip()
            return True
        return posted

    # =============================================================================
    # Poll & TOD
    # =============================================================================
    def maybe_post_tod(self):
        today_key = day_key()
        if self.state.get("tod_day_key") == today_key:
            return
        pillar = self.state.get("last_poll_pillar") or "نصائح تقنية يومية"
        choice = None
        if self.state.get("last_poll_id") and not self.state.get("last_poll_processed"):
            winner = self.fetch_poll_winner(self.state["last_poll_id"])
            if winner:
                choice = winner
                self.state["last_poll_processed"] = True
                logger.info(f"🎯 TOD winner from poll: {choice}")
            else:
                logger.info("⚠️ لم أتمكن من قراءة نتيجة الاستفتاء - سأستخدم اختيارًا احتياطيًا.")
        if not choice:
            level = self.state.get("last_poll_level") or "beginner"
            options = POLL_CONFIG.get(pillar, {}).get("levels", {}).get(level, {}).get("options", [])
            choice = options[0] if options else "AI يومي"

        system = ("اكتب نصيحة تقنية قصيرة بالعربية وواضحة ومباشرة، مفيدة للمستخدم العربي اليوم. "
                  "لا تتجاوز 280 حرفًا. لا هاشتاقات داخل النص. اختم بسؤال بسيط (CTA).")
        user = f"المجال: {pillar}\nالموضوع الفائز/المختار: {choice}"
        text = call_ai(system, user, max_tokens=220, temperature=0.8) or \
               f"نصيحة اليوم عن «{choice}». ما أفضل حيلة عندك في هذا الموضوع؟"
        if SIGNATURE:
            text += f"\n{SIGNATURE}"

        self.post_tweet(text)
        self.state["tod_day_key"] = today_key
        self.state["tod_pillar"] = pillar
        self.state["tod_choice"] = choice
        self._save_state()

    def maybe_post_poll(self):
        if not POLL_MODE:
            return
        last = self.state.get("last_poll_at")
        if last:
            last_dt = datetime.fromisoformat(last)
            if datetime.now(timezone.utc) - last_dt < timedelta(days=POLL_EVERY_DAYS):
                return

        pillars = list(POLL_CONFIG.keys())
        p_idx = self.state.get("poll_pillar_index", 0) % len(pillars)
        pillar = pillars[p_idx]
        levels = ["beginner", "intermediate", "advanced"]
        l_idx = self.state.get("poll_level_index", 0) % len(levels)
        level = levels[l_idx]
        cfg = POLL_CONFIG[pillar]["levels"][level]
        options = cfg["options"][:4]
        question = POLL_CONFIG[pillar]["question"]

        tid = self.create_poll(f"{question}\n({level})", options, POLL_DURATION_MINUTES)
        if tid:
            self.state["last_poll_id"] = tid
            self.state["last_poll_at"] = utcnow_iso()
            self.state["last_poll_pillar"] = pillar
            self.state["last_poll_level"] = level
            self.state["last_poll_processed"] = False
            self.state["poll_pillar_index"] = (p_idx + 1) % len(pillars)
            self.state["poll_level_index"]  = (l_idx + 1) % len(levels)
            self._save_state()

    # =============================================================================
    # Dashboard / Errors
    # =============================================================================
    def show_dashboard(self):
        if not SHOW_DASHBOARD:
            return
        logger.info("------ DASHBOARD ------")
        logger.info(f"Month: {self.state.get('month_key')}")
        logger.info(f"Posts this month: {self.state.get('posts_this_month')}")
        logger.info(f"Last poll: {self.state.get('last_poll_at')} ({self.state.get('last_poll_pillar')}/{self.state.get('last_poll_level')})")
        logger.info(f"TOD: {self.state.get('tod_day_key')} - {self.state.get('tod_pillar')} / {self.state.get('tod_choice')}")
        logger.info("-----------------------")

    def _bump_error(self):
        self.state["errors_last_run"] = self.state.get("errors_last_run", 0) + 1
        if AUTO_KILL_ON_ERRORS and self.state["errors_last_run"] >= MAX_ERRORS_PER_RUN:
            kill_until = datetime.now(timezone.utc) + timedelta(minutes=KILL_COOLDOWN_MINUTES)
            self.state["reply_kill_until"] = kill_until.isoformat()
            logger.error(f"🚫 Too many errors. Killing replies until {kill_until.isoformat()}")

    # =============================================================================
    # التشغيل
    # =============================================================================
    def run(self):
        if COMPLIANCE_MODE_ENABLED and self._is_locked():
            logger.info("🛡️ Compliance lock active — سيتم تخفيف النشر عبر المجدول.")

        if in_quiet_hours(QUIET_HOURS_UTC):
            logger.info("⏳ هدوء (Quiet Hours) — لا نشر الآن.")
            return

        mk = month_key()
        if self.state.get("month_key") != mk:
            self.state["month_key"] = mk
            self.state["posts_this_month"] = 0
            self.state["reads_this_month"] = 0
            self.state["post_times_15m"] = []
            self._save_state()

        posted = self.do_scheduled_post()
        self.process_mentions()
        self.show_dashboard()


# =============================================================================
# الدخول الرئيسي
# =============================================================================
if __name__ == "__main__":
    try:
        bot = TechBot()
        bot.run()
        logger.info("🏁 Done.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        _ensure_parent_dir(AUDIT_LOG)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": utcnow_iso(),
                "type": "fatal_error",
                "payload": {"error": str(e)},
            }, ensure_ascii=False) + "\n")
        raise
