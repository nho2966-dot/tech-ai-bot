# -*- coding: utf-8 -*-
"""
Tech AI Bot (X) — Production
- RSS threads + tips
- Daily Tech Tips pillar + Poll
- Topic of the Day: daily tip guided by last poll winner (if accessible)
- Mention replies with anti-dup + safety throttles
- Growth boosters + daily questions + trending snippets
- Media cards (images) + short video threads (pin last if enabled)
- State persisted to state.json + audit_log.jsonl at repo root
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
from PIL import Image, ImageDraw, ImageFont, ImageOps  # لبطاقات الميديا

# =============================================================================
# ثابت المسارات: خزّن الملفات في جذر المشروع (tech-ai-bot/)
# =============================================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))        # -> tech-ai-bot/
LOG_DIR = os.path.join(ROOT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
STATE_FILE = os.path.join(ROOT_DIR, "state.json")
AUDIT_LOG = os.path.join(ROOT_DIR, "audit_log.jsonl")

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

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # Rotating file
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024,
                                              backupCount=5, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid handler duplication if reloaded
    while root.handlers:
        root.removeHandler(root.handlers[0])

    root.addHandler(ch)
    root.addHandler(fh)

setup_logging()
logger = logging.getLogger(__name__)
logger.info("🚀 Tech AI Bot starting up...")

# =============================================================================
# ثوابت عامة
# =============================================================================
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
DIGIT_RE = re.compile(r"\d+")

TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"

# Plan guards (Basic)
POST_CAP_MONTHLY = int(os.getenv("POST_CAP_MONTHLY", "3000"))
READ_CAP_MONTHLY = int(os.getenv("READ_CAP_MONTHLY", "15000"))
POSTS_PER_15MIN_SOFT = int(os.getenv("POSTS_PER_15MIN_SOFT", "95"))

# Modes
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
SOURCE_MODE = os.getenv("SOURCE_MODE", "1") == "1"
POLL_MODE = os.getenv("POLL_MODE", "1") == "1"
TIP_MODE = os.getenv("TIP_MODE", "1") == "1"
SHOW_DASHBOARD = os.getenv("SHOW_DASHBOARD", "0") == "1"
SEND_RECOMMENDATION = os.getenv("SEND_RECOMMENDATION", "0") == "1"

POLL_EVERY_DAYS = int(os.getenv("POLL_EVERY_DAYS", "7"))
POLL_DURATION_MINUTES = int(os.getenv("POLL_DURATION_MINUTES", "1440"))
METRICS_DELAY_SECONDS = int(os.getenv("METRICS_DELAY_SECONDS", "120"))

# Reply safety knobs
REPLY_ENABLED = os.getenv("REPLY_ENABLED", "1") == "1"
MAX_REPLIES_PER_RUN = int(os.getenv("MAX_REPLIES_PER_RUN", "2"))
MAX_REPLIES_PER_HOUR = int(os.getenv("MAX_REPLIES_PER_HOUR", "4"))
MAX_REPLIES_PER_DAY = int(os.getenv("MAX_REPLIES_PER_DAY", "12"))
MAX_REPLIES_PER_USER_PER_DAY = int(os.getenv("MAX_REPLIES_PER_USER_PER_DAY", "1"))
REPLY_COOLDOWN_HOURS = int(os.getenv("REPLY_COOLDOWN_HOURS", "12"))
REPLY_JITTER_MIN = float(os.getenv("REPLY_JITTER_MIN", "2"))
REPLY_JITTER_MAX = float(os.getenv("REPLY_JITTER_MAX", "6"))
QUIET_HOURS_UTC = os.getenv("QUIET_HOURS_UTC", "0-5")
AUTO_KILL_ON_ERRORS = os.getenv("AUTO_KILL_ON_ERRORS", "1") == "1"
MAX_ERRORS_PER_RUN = int(os.getenv("MAX_ERRORS_PER_RUN", "3"))
KILL_COOLDOWN_MINUTES = int(os.getenv("KILL_COOLDOWN_MINUTES", "180"))

LEVELS = ["beginner", "intermediate", "advanced"]

DEFAULT_HASHTAGS = ["#تقنية", "#برمجة"]
MAX_HASHTAGS = int(os.getenv("MAX_HASHTAGS", "2"))
SIGNATURE = os.getenv("SIGNATURE", "").strip()

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# ====== X Premium features ======
PIN_LAST = os.getenv("PIN_LAST", "1") == "1"          # تثبيت آخر تغريدة مهمة تلقائيًا
MEDIA_CARDS = os.getenv("MEDIA_CARDS", "1") == "1"    # بطاقات صورة للنصوص القصيرة
CARD_BRAND = os.getenv("CARD_BRAND", "Tech AI Bot")   # توقيع بسيط أسفل البطاقة
CARD_FONT_PATHS = [
    os.path.join(ROOT_DIR, "font.ttf"),               # خط عربي في الجذر
    os.path.join(THIS_DIR, "font.ttf"),               # أو نسخة داخل src
]

# ====== FailSafe ======
FAILSAFE_ENABLED = os.getenv("FAILSAFE_ENABLED", "1") == "1"
FAILSAFE_PILLARS = [p.strip() for p in os.getenv("FAILSAFE_PILLARS", "smart_devices,ai").split(",") if p.strip()]

# ====== Video (short clips) ======
VIDEO_ENABLED = os.getenv("VIDEO_ENABLED", "1") == "1"
VIDEO_PATH = os.getenv("VIDEO_PATH", "").strip()           # ملف فيديو محدد (اختياري)
VIDEO_DIR = os.getenv("VIDEO_DIR", "").strip()             # مجلد الفيديوهات (افتراضي: web/ في الجذر)
VIDEO_MAX_MB = int(os.getenv("VIDEO_MAX_MB", "50"))        # حجم أقصى للملف (MB)
VIDEO_MAX_SECONDS = int(os.getenv("VIDEO_MAX_SECONDS", "75"))  # مدة قصوى (ثواني) إن توفرت
VIDEO_EXTS = (".mp4", ".mov", ".m4v")

# ====== Video Thread ======
VIDEO_THREAD_ENABLED = os.getenv("VIDEO_THREAD_ENABLED", "1") == "1"
VIDEO_THREAD_POINTS = int(os.getenv("VIDEO_THREAD_POINTS", "2"))  # عدد النقاط النصية التابعة (2–3)

# ====== Part Labels ======
PART_LABEL_ENABLED = os.getenv("PART_LABEL_ENABLED", "1") == "1"
PART_LABEL_STYLE = os.getenv("PART_LABEL_STYLE", "prefix")     # 'prefix' أو 'suffix'
PART_LABEL_LOCALIZED = os.getenv("PART_LABEL_LOCALIZED", "1") == "1"  # 'الجزء 1/2' بدل 'Part 1/2'

# =============================================================================
# تكوين الاستفتاءات والمصادر
# =============================================================================
POLL_CONFIG: Dict[str, Dict[str, Any]] = {
    "الذكاء الاصطناعي": {
        "question": "وين تحب نركّز في ثريد AI القادم؟ 🤖",
        "levels": {
            "beginner": {
                "options": ["وش هو AI أصلًا؟", "كيف أبدأ؟", "أفضل أدوات", "أمثلة بسيطة"],
                "keywords": {
                    "وش هو AI أصلًا؟": ["what is ai", "basics", "introduction"],
                    "كيف أبدأ؟": ["getting started", "first steps"],
                    "أفضل أدوات": ["tools", "beginner", "no code"],
                    "أمثلة بسيطة": ["example", "use case", "demo"],
                },
            },
            "intermediate": {
                "options": ["المخرجات غير دقيقة", "الشرح مو واضح", "التكلفة مرتفعة", "تحسين الاستخدام"],
                "keywords": {
                    "المخرجات غير دقيقة": ["evaluation", "hallucination", "quality"],
                    "الشرح مو واضح": ["prompt", "explainability"],
                    "التكلفة مرتفعة": ["cost", "pricing", "tokens", "billing"],
                    "تحسين الاستخدام": ["best practices", "optimization"],
                },
            },
            "advanced": {
                "options": ["RAG بشكل صحيح", "Agents عمليًا", "تقييم المخرجات", "أمان النماذج"],
                "keywords": {
                    "RAG بشكل صحيح": ["rag", "vector", "retrieval", "embedding"],
                    "Agents عمليًا": ["agentic", "workflow", "orchestration"],
                    "تقييم المخرجات": ["eval", "benchmark"],
                    "أمان النماذج": ["safety", "guardrails", "security"],
                },
            },
        },
    },
    "الحوسبة السحابية": {
        "question": "إيش أكثر شيء يرهقك في السحابة؟ ☁️",
        "levels": {
            "beginner": {
                "options": ["وش هي السحابة؟", "أول خدمة أتعلمها", "فرق AWS وAzure", "أمثلة استخدام"],
                "keywords": {
                    "وش هي السحابة؟": ["cloud basics", "introduction"],
                    "أول خدمة أتعلمها": ["getting started", "compute"],
                    "فرق AWS وAzure": ["aws vs azure"],
                    "أمثلة استخدام": ["use case", "example"],
                },
            },
            "intermediate": {
                "options": ["ارتفاع التكاليف", "التعقيد", "الأمان", "الاعتمادية"],
                "keywords": {
                    "ارتفاع التكاليف": ["finops", "cost", "billing", "spend"],
                    "التعقيد": ["architecture", "design", "complexity"],
                    "الأمان": ["security", "iam", "zero trust", "compliance"],
                    "الاعتمادية": ["reliability", "resilience", "availability"],
                },
            },
            "advanced": {
                "options": ["FinOps متقدم", "Zero Trust", "Multi‑Cloud", "SRE عملي"],
                "keywords": {
                    "FinOps متقدم": ["finops", "governance"],
                    "Zero Trust": ["zero trust", "identity", "entra"],
                    "Multi‑Cloud": ["multi cloud", "hybrid"],
                    "SRE عملي": ["sre", "slo", "error budget", "observability"],
                },
            },
        },
    },
    "البرمجة": {
        "question": "إيش أكثر شيء يضيّع وقتك في البرمجة؟ 👨‍💻",
        "levels": {
            "beginner": {
                "options": ["من وين أبدأ؟", "لغة أتعلمها", "أمثلة بسيطة", "أخطاء شائعة"],
                "keywords": {
                    "من وين أبدأ؟": ["getting started", "roadmap"],
                    "لغة أتعلمها": ["language choice", "beginner"],
                    "أمثلة بسيطة": ["tutorial", "example"],
                    "أخطاء شائعة": ["common mistakes"],
                },
            },
            "intermediate": {
                "options": ["Debugging", "اختبارات", "تنظيم الكود", "أداء التطبيق"],
                "keywords": {
                    "Debugging": ["debug", "bug", "error"],
                    "اختبارات": ["testing", "unit test", "integration"],
                    "تنظيم الكود": ["refactor", "clean code", "maintain"],
                    "أداء التطبيق": ["performance", "profiling", "latency"],
                },
            },
            "advanced": {
                "options": ["Refactoring كبير", "أداء عالي", "أنماط معمارية", "Scalability"],
                "keywords": {
                    "Refactoring كبير": ["legacy", "refactor"],
                    "أداء عالي": ["low latency", "high performance", "profil"],
                    "أنماط معمارية": ["architecture", "patterns"],
                    "Scalability": ["scaling", "distributed", "throughput"],
                },
            },
        },
    },
    "نصائح تقنية يومية": {
        "question": "وش تحب نصيحة اليوم تكون عن؟ 💡",
        "levels": {
            "beginner": {
                "options": ["AI يومي", "أجهزة ذكية", "مواقع التواصل", "خصوصية وأمان"],
                "keywords": {
                    "AI يومي": ["chatgpt", "prompt", "ai"],
                    "أجهزة ذكية": ["iphone", "android", "pixel", "smartwatch"],
                    "مواقع التواصل": ["instagram", "whatsapp", "facebook"],
                    "خصوصية وأمان": ["privacy", "security", "scam"],
                },
            },
            "intermediate": {
                "options": ["AI يومي", "أجهزة ذكية", "مواقع التواصل", "خصوصية وأمان"],
                "keywords": {
                    "AI يومي": ["chatgpt", "prompt", "ai"],
                    "أجهزة ذكية": ["iphone", "android", "pixel", "smartwatch"],
                    "مواقع التواصل": ["instagram", "whatsapp", "facebook"],
                    "خصوصية وأمان": ["privacy", "security", "scam"],
                },
            },
            "advanced": {
                "options": ["AI يومي", "أجهزة ذكية", "مواقع التواصل", "خصوصية وأمان"],
                "keywords": {
                    "AI يومي": ["chatgpt", "prompt", "ai"],
                    "أجهزة ذكية": ["iphone", "android", "pixel", "smartwatch"],
                    "مواقع التواصل": ["instagram", "whatsapp", "facebook"],
                    "خصوصية وأمان": ["privacy", "security", "scam"],
                },
            },
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
# وظائف مساعدة
# =============================================================================
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def in_quiet_hours(cfg: str) -> bool:
    """cfg مثال: "0-5" يعني من 00:00 حتى 05:59 UTC"""
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

def clamp_tweet(text: str) -> str:
    if len(text) <= TWEET_LIMIT:
        return text
    return text[: TWEET_LIMIT - 1] + "…"

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
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "summary": desc})
    # Atom
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = (link_el.get("href") if link_el is not None else "").strip()
        summary = (entry.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "summary": summary})
    return items

# =============================================================================
# واجهة OpenRouter (openai 2.x)
# =============================================================================
def call_ai(system_prompt: str, user_prompt: str, model: str = OPENROUTER_MODEL,
            max_tokens: int = 800, temperature: float = 0.7) -> str:
    """يستخدم Chat Completions المتوافق مع OpenRouter ويعيد نصًا."""
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
    """إنشاء ثريد من عدة تغريدات مفصولة بـ THREAD_DELIM، مع إضافة رابط المصدر في النهاية."""
    instr = (
        "اكتب كمختص تقني عربي بأسلوب بسيط وودود.\n"
        "كل تغريدة لا تتجاوز 280 حرفًا.\n"
        "التزم: Hook ثم Value ثم CTA (سؤال لطيف).\n"
        "لا تضع هاشتاقات داخل النص.\n"
        "لا تضع روابط داخل النص؛ سنضيف رابط المصدر في آخر تغريدة بسطر مستقل يبدأ بـ 'المصدر:'.\n"
        "اجعل الثريد مباشرًا وواضحًا ومفيدًا للقارئ العربي، مع أمثلة مختصرة إن لزم.\n"
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
            last = clamp_tweet(last + suffix)
            tweets[-1] = last
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

        # OpenRouter عبر مكتبة openai (2.x)
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=os.getenv("OPENROUTER_API_KEY"))
        TechBot._ai_client = self.ai

        # عميل X (Twitter) عبر tweepy v4
        self.x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )

        # API v1.1 للوسائط
        self._init_api_v1()

        self._me_id: Optional[str] = None
        self.api_v1 = getattr(self, "api_v1", None)

        self.state = self._load_state()
        logger.info("📌 Profile Checklist: Bio واضح + Pin أفضل ثريد + Banner وعد قيمة")

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

        # Topic of the Day
        s.setdefault("tod_day_key", None)
        s.setdefault("tod_pillar", None)
        s.setdefault("tod_choice", None)
        s.setdefault("tod_keywords", [])
        s.setdefault("tod_poll_id", None)

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
    # v1.1 Media API (صور/فيديو) + تهيئة
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
    # بطاقات مرئية بسيطة للنصائح/الأسئلة
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
            body_font = self._load_font(44)
            brand_font = self._load_font(32)

            margin = 60
            y = margin
            draw.text((margin, y), title, font=title_font, fill=(56, 189, 248))
            y += 90

            def wrap(text, font, max_width):
                words = text.split()
                lines = []
                line = ""
                for w_ in words:
                    test = (line + " " + w_).strip()
                    if draw.textlength(test, font=font) <= max_width:
                        line = test
                    else:
                        if line:
                            lines.append(line)
                        line = w_
                if line:
                    lines.append(line)
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
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Tweet: {text} | media={media_ids} | reply_to={reply_to}")
            return "dryrun-0"
        try:
            if reply_to:
                resp = self.x.create_tweet(text=text, in_reply_to_tweet_id=reply_to,
                                           media={"media_ids": media_ids} if media_ids else None)
            else:
                resp = self.x.create_tweet(text=text, media={"media_ids": media_ids} if media_ids else None)
            tid = resp.data["id"]  # type: ignore
            logger.info(f"✅ Posted tweet: {tid}")
            self._audit("tweet_posted", {"tweet_id": tid, "reply_to": reply_to, "text": text})
            return tid
        except Exception as e:
            logger.error(f"❌ Tweet failed: {e}")
            self._audit("tweet_error", {"error": str(e), "text": text})
            self._bump_error()
            return None

    def post_thread(self, tweets: List[str]) -> Optional[str]:
        if not tweets:
