# -*- coding: utf-8 -*-
"""
Tech AI Bot (X) — Production
- Ultra Smart Scheduler (slots + weekly plan + engagement-aware + rotation)
- Auto-Compliance (locks + soft feature-off + prechecks)
- Failsafe tips (smart devices / AI) + Threads from RSS
- Short Video Threads (v1.1 chunked upload) + Media Cards (Pillow)
- Smart Reply Inspector 2.0 (anti-dup + intent + soft tone)
- Strict Toxicity Filter (multi-layer) + professional non-confrontational replies
- Skip self-replies + bot-like accounts
- State persisted at repo root (state.json / audit_log.jsonl)
- Logs at logs/bot.log (rotating)
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
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# مسارات مرنة: يتعرّف تلقائيًا على جذر المشروع سواء كان main.py في الجذر أو src/
# =============================================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

def _detect_root(base: str) -> str:
    """
    يحاول اكتشاف جذر المشروع الفعلي:
    - إذا احتوى base على src/ + requirements.txt → اعتبره الجذر
    - وإلا جرّب الأب أو tech-ai-bot/ إن وُجد
    """
    candidates = [
        base,
        os.path.abspath(os.path.join(base, "..")),
        os.path.abspath(os.path.join(base, "tech-ai-bot")),
        os.path.abspath(os.path.join(base, "..", "tech-ai-bot")),
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, "src")) and os.path.isfile(os.path.join(c, "requirements.txt")):
            return c
    # كحل أخير: الأب
    return os.path.abspath(os.path.join(base, ".."))

ROOT_DIR = _detect_root(THIS_DIR)
SRC_DIR  = os.path.join(ROOT_DIR, "src")
LOG_DIR  = os.path.join(ROOT_DIR, "logs")
WEB_DIR  = os.path.join(ROOT_DIR, "web")

STATE_FILE = os.path.join(ROOT_DIR, "state.json")
AUDIT_LOG  = os.path.join(ROOT_DIR, "audit_log.jsonl")

# =============================================================================
# أدوات مساعدة للملفات واللوج
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

    fh = logging.handlers.RotatingFileHandler(os.path.join(LOG_DIR, "bot.log"),
                                              maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8")
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
logger.info("🚀 Tech AI Bot starting with flexible paths…")
logger.info(f"ROOT_DIR={ROOT_DIR} | SRC_DIR={SRC_DIR} | LOG_DIR={LOG_DIR} | WEB_DIR={WEB_DIR}")

# =============================================================================
# ثوابت عامة
# =============================================================================
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"

# Plan guards
POST_CAP_MONTHLY = int(os.getenv("POST_CAP_MONTHLY", "3000"))
READ_CAP_MONTHLY = int(os.getenv("READ_CAP_MONTHLY", "15000"))
POSTS_PER_15MIN_SOFT = int(os.getenv("POSTS_PER_15MIN_SOFT", "95"))

# Modes
DRY_RUN           = os.getenv("DRY_RUN", "0") == "1"
SOURCE_MODE       = os.getenv("SOURCE_MODE", "1") == "1"
POLL_MODE         = os.getenv("POLL_MODE", "1") == "1"
TIP_MODE          = os.getenv("TIP_MODE", "1") == "1"
SHOW_DASHBOARD    = os.getenv("SHOW_DASHBOARD", "0") == "1"
SEND_RECOMMENDATION = os.getenv("SEND_RECOMMENDATION", "0") == "1"

POLL_EVERY_DAYS   = int(os.getenv("POLL_EVERY_DAYS", "7"))
POLL_DURATION_MINUTES = int(os.getenv("POLL_DURATION_MINUTES", "1440"))

# Replies safety
REPLY_ENABLED                  = os.getenv("REPLY_ENABLED", "1") == "1"
MAX_REPLIES_PER_RUN            = int(os.getenv("MAX_REPLIES_PER_RUN", "2"))
MAX_REPLIES_PER_HOUR           = int(os.getenv("MAX_REPLIES_PER_HOUR", "4"))
MAX_REPLIES_PER_DAY            = int(os.getenv("MAX_REPLIES_PER_DAY", "12"))
MAX_REPLIES_PER_USER_PER_DAY   = int(os.getenv("MAX_REPLIES_PER_USER_PER_DAY", "1"))
REPLY_COOLDOWN_HOURS           = int(os.getenv("REPLY_COOLDOWN_HOURS", "12"))
REPLY_JITTER_MIN               = float(os.getenv("REPLY_JITTER_MIN", "2"))
REPLY_JITTER_MAX               = float(os.getenv("REPLY_JITTER_MAX", "6"))
QUIET_HOURS_UTC                = os.getenv("QUIET_HOURS_UTC", "0-5")
AUTO_KILL_ON_ERRORS            = os.getenv("AUTO_KILL_ON_ERRORS", "1") == "1"
MAX_ERRORS_PER_RUN             = int(os.getenv("MAX_ERRORS_PER_RUN", "3"))
KILL_COOLDOWN_MINUTES          = int(os.getenv("KILL_COOLDOWN_MINUTES", "180"))

DEFAULT_HASHTAGS = ["#تقنية", "#برمجة"]
MAX_HASHTAGS     = int(os.getenv("MAX_HASHTAGS", "2"))
SIGNATURE        = os.getenv("SIGNATURE", "").strip()

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# X Premium / Media Cards
PIN_LAST     = os.getenv("PIN_LAST", "1") == "1"
MEDIA_CARDS  = os.getenv("MEDIA_CARDS", "1") == "1"
CARD_BRAND   = os.getenv("CARD_BRAND", "Tech AI Bot")
CARD_FONT_PATHS = [
    os.path.join(ROOT_DIR, "font.ttf"),
    os.path.join(SRC_DIR, "font.ttf"),
]

# Failsafe
FAILSAFE_ENABLED = os.getenv("FAILSAFE_ENABLED", "1") == "1"
FAILSAFE_PILLARS = [p.strip() for p in os.getenv("FAILSAFE_PILLARS", "smart_devices,ai").split(",") if p.strip()]

# Video
VIDEO_ENABLED           = os.getenv("VIDEO_ENABLED", "1") == "1"
VIDEO_PATH              = os.getenv("VIDEO_PATH", "").strip()
VIDEO_DIR               = os.getenv("VIDEO_DIR", "web").strip()  # بالنسبة للجذر
VIDEO_MAX_MB            = int(os.getenv("VIDEO_MAX_MB", "50"))
VIDEO_MAX_SECONDS       = int(os.getenv("VIDEO_MAX_SECONDS", "75"))
VIDEO_THREAD_ENABLED    = os.getenv("VIDEO_THREAD_ENABLED", "1") == "1"
VIDEO_THREAD_POINTS     = int(os.getenv("VIDEO_THREAD_POINTS", "2"))
VIDEO_EXTS              = (".mp4", ".mov", ".m4v")

# Smart Reply Inspector 2.0
SMART_REPLY_STRICT   = os.getenv("SMART_REPLY_STRICT", "1") == "1"
SMART_REPLY_SOFT_TONE= os.getenv("SMART_REPLY_SOFT_TONE", "1") == "1"
SMART_REPLY_INTENT   = os.getenv("SMART_REPLY_INTENT", "1") == "1"
NO_REPLY_TO_SELF     = os.getenv("NO_REPLY_TO_SELF", "1") == "1"
NO_REPLY_TO_BOTS     = os.getenv("NO_REPLY_TO_BOTS", "1") == "1"
BOT_KEYWORDS         = [kw.strip().lower() for kw in os.getenv("BOT_KEYWORDS", "bot,بوت,automated,automation,🤖").split(",") if kw.strip()]
REPLY_MIN_LEN        = int(os.getenv("REPLY_MIN_LEN", "25"))
REPLY_SIM_THRESHOLD  = float(os.getenv("REPLY_SIM_THRESHOLD", "0.75"))
REPLY_HASH_WINDOW    = int(os.getenv("REPLY_HASH_WINDOW", "200"))

# Strict Toxicity
TOXIC_STRICT_ENABLED           = os.getenv("TOXIC_STRICT_ENABLED", "1") == "1"
TOXIC_USER_COOLDOWN_HOURS      = int(os.getenv("TOXIC_USER_COOLDOWN_HOURS", "24"))
HOSTILE_USER_COOLDOWN_MINUTES  = int(os.getenv("HOSTILE_USER_COOLDOWN_MINUTES", "90"))
TOXIC_SCORE_THRESHOLD          = float(os.getenv("TOXIC_SCORE_THRESHOLD", "0.65"))
HOSTILE_SCORE_THRESHOLD        = float(os.getenv("HOSTILE_SCORE_THRESHOLD", "0.40"))
TOXIC_WINDOW_MINUTES           = int(os.getenv("TOXIC_WINDOW_MINUTES", "60"))
TOXIC_MAX_MATCHES              = int(os.getenv("TOXIC_MAX_MATCHES", "2"))
TOXIC_WHITELIST_TERMS          = [t.strip() for t in os.getenv("TOXIC_WHITELIST_TERMS", "نقد,تصحيح,اقتراح").split(",") if t.strip()]

# Smart Scheduling (Ultra)
SCHED_MODE = os.getenv("SCHED_MODE", "ultra")
LOCAL_TZ_OFFSET_MINUTES = int(os.getenv("LOCAL_TZ_OFFSET_MINUTES", "240"))
SLOTS_DEF  = os.getenv("SLOTS_DEF", "rss=11-17;tip=19-22;video=12-15;question=15-20;poll=18-21;trending=14-18;booster=16-20")
WEEKLY_PLAN = os.getenv("WEEKLY_PLAN", "sun=video,rss;mon=rss,tip;tue=question,rss;wed=tip,trending;thu=video,booster;fri=poll,tip;sat=tip,booster")
ENGAGEMENT_HIGH_THRESHOLD = int(os.getenv("ENGAGEMENT_HIGH_THRESHOLD", "4"))
ENGAGEMENT_COOLDOWN_MINUTES = int(os.getenv("ENGAGEMENT_COOLDOWN_MINUTES", "45"))
RANDOM_SKIP_CHANCE = float(os.getenv("RANDOM_SKIP_CHANCE", "0.25"))

# Auto‑Compliance
COMPLIANCE_MODE_ENABLED          = os.getenv("COMPLIANCE_MODE_ENABLED", "1") == "1"
COMPLIANCE_MAX_POSTS_PER_DAY     = int(os.getenv("COMPLIANCE_MAX_POSTS_PER_DAY", "8"))
COMPLIANCE_MAX_ERRORS_PER_WINDOW = int(os.getenv("COMPLIANCE_MAX_ERRORS_PER_WINDOW", "3"))
COMPLIANCE_WINDOW_MINUTES        = int(os.getenv("COMPLIANCE_WINDOW_MINUTES", "60"))
COMPLIANCE_MIN_INTERVAL_MINUTES  = int(os.getenv("COMPLIANCE_MIN_INTERVAL_MINUTES", "20"))
COMPLIANCE_LOCK_DURATION_MINUTES = int(os.getenv("COMPLIANCE_LOCK_DURATION_MINUTES", "180"))
COMPLIANCE_QUIET_HOURS_EXTENSION = int(os.getenv("COMPLIANCE_QUIET_HOURS_EXTENSION", "2"))
COMPLIANCE_STRICT_MODE           = os.getenv("COMPLIANCE_STRICT_MODE", "1") == "1"

# =============================================================================
# RSS و Polls
# =============================================================================
POLL_CONFIG: Dict[str, Dict[str, Any]] = {
    "الذكاء الاصطناعي": {
        "question": "وين تحب نركّز في ثريد AI القادم؟ 🤖",
        "levels": {
            "beginner": {"options": ["وش هو AI أصلًا؟", "كيف أبدأ؟", "أفضل أدوات", "أمثلة بسيطة"]},
            "intermediate": {"options": ["المخرجات غير دقيقة", "الشرح مو واضح", "التكلفة مرتفعة", "تحسين الاستخدام"]},
            "advanced": {"options": ["RAG بشكل صحيح", "Agents عمليًا", "تقييم المخرجات", "أمان النماذج"]},
        },
    },
    "الحوسبة السحابية": {
        "question": "إيش أكثر شيء يرهقك في السحابة؟ ☁️",
        "levels": {
            "beginner": {"options": ["وش هي السحابة؟", "أول خدمة أتعلمها", "فرق AWS وAzure", "أمثلة استخدام"]},
            "intermediate": {"options": ["ارتفاع التكاليف", "التعقيد", "الأمان", "الاعتمادية"]},
            "advanced": {"options": ["FinOps متقدم", "Zero Trust", "Multi‑Cloud", "SRE عملي"]},
        },
    },
    "البرمجة": {
        "question": "إيش أكثر شيء يضيّع وقتك في البرمجة؟ 👨‍💻",
        "levels": {
            "beginner": {"options": ["من وين أبدأ؟", "لغة أتعلمها", "أمثلة بسيطة", "أخطاء شائعة"]},
            "intermediate": {"options": ["Debugging", "اختبارات", "تنظيم الكود", "أداء التطبيق"]},
            "advanced": {"options": ["Refactoring كبير", "أداء عالي", "أنماط معمارية", "Scalability"]},
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
# وظائف عامة
# =============================================================================
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def clamp_tweet(text: str) -> str:
    return text if len(text) <= TWEET_LIMIT else (text[: TWEET_LIMIT - 1] + "…")

def sleep_jitter(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

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
    # RSS
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "summary": desc})
    # Atom
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title   = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link    = (link_el.get("href") if link_el is not None else "").strip()
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
        "لا هاشتاقات داخل النص.\n"
        "لا روابط داخل النص؛ سنضيف رابط المصدر في آخر تغريدة.\n"
    )
    user = (
        f"المصدر يتحدث عن: «{title}»\n"
        f"ملخص: {summary or 'لا يوجد'}\n"
        f"الركيزة: {pillar}\n"
        f"افصل بين التغريدات بالرمز {THREAD_DELIM!r}\n"
    )
    text = call_ai(instr, user)
    if not text:
        tweets = [
            f"📌 جديد في {pillar}: {title}",
            "الخلاصة: نقطة/نقطتان مفيدتان من المصدر.",
            "رأيك؟ هل تريد تفاصيل أكثر؟"
        ]
    else:
        tweets = [t.strip() for t in text.split(THREAD_DELIM) if t.strip()]
    if source_url:
        if tweets:
            tweets[-1] = clamp_tweet(tweets[-1] + f"\nالمصدر: {source_url}")
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

        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        TechBot._ai_client = self.ai

        self.x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )
        self._init_api_v1()  # للوسائط (صور/فيديو) عبر v1.1

        self._me_id: Optional[str] = None
        self.state = self._load_state()
        logger.info("📌 Ready with Smart Scheduler + Compliance + Media + Replies")

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

        # posting guards
        s.setdefault("used_links", [])
        s.setdefault("month_key", None)
        s.setdefault("posts_this_month", 0)
        s.setdefault("reads_this_month", 0)
        s.setdefault("post_times_15m", [])

        # polls
        s.setdefault("last_poll_at", None)
        s.setdefault("last_poll_id", None)
        s.setdefault("last_poll_pillar", None)
        s.setdefault("last_poll_level", None)
        s.setdefault("last_poll_processed", False)
        s.setdefault("poll_pillar_index", 0)
        s.setdefault("poll_level_index", 0)
        s.setdefault("poll_perf", {})

        # replies
        s.setdefault("last_mention_id", None)
        s.setdefault("replied_to_ids", [])
        s.setdefault("recent_reply_hashes", [])
        s.setdefault("reply_user_cooldown", {})
        s.setdefault("reply_times_1h", [])
        s.setdefault("reply_day_key", None)
        s.setdefault("replies_today", 0)
        s.setdefault("replies_today_by_user", {})
        s.setdefault("opt_out_users", [])
        s.setdefault("reply_kill_until", None)
        s.setdefault("errors_last_run", 0)

        # TOD
        s.setdefault("tod_day_key", None)
        s.setdefault("tod_pillar", None)
        s.setdefault("tod_choice", None)
        s.setdefault("tod_keywords", [])
        s.setdefault("tod_poll_id", None)

        # Smart replies
        s.setdefault("recent_reply_texts", [])
        s.setdefault("user_reply_hashes", {})

        # Strict toxicity
        s.setdefault("toxic_user_block_until", {})
        s.setdefault("hostile_user_cooldown_until", {})
        s.setdefault("recent_toxic_hits", [])

        # scheduling stats
        s.setdefault("last_content_type", None)
        s.setdefault("content_counts_today", {})
        s.setdefault("last_counts_day", None)

        return s

    def _save_state(self):
        _ensure_parent_dir(STATE_FILE)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _audit(self, event_type: str, payload: dict, content_type: str = None):
        _ensure_parent_dir(AUDIT_LOG)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": utcnow_iso(),
                "type": event_type,
                "content_type": content_type,
                "payload": payload,
            }, ensure_ascii=False) + "\n")

    # =============================================================================
    # v1.1 Media API (صور/فيديو)
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
    # Cards
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

            def wrap(text: str, font, max_width: int):
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

            max_text_width = w - (margin * 2)
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

    def post_tweet(self, text: str, reply_to: Optional[str] = None, media_ids: Optional[List[str]] = None) -> Optional[str]:
        text = clamp_tweet(text)

        # Compliance precheck
