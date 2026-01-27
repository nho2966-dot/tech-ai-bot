# -*- coding: utf-8 -*-
"""Tech AI Bot (X) — Basic Plan — Final main.py (with Daily Tech Tips pillar + poll + safety)

What this bot does
- Posts:
  - RSS-driven Threads (SOURCE_MODE) with credibility gate (no extra URLs, no unsupported numbers)
  - Tip posts (short, practical) on Tue/Thu by default
  - A dedicated pillar: "نصائح تقنية يومية" is biased to Tip format (daily practical value)
- Poll mode:
  - per-pillar + per-level polls; learns which audience level performs better
  - includes a dedicated poll for "نصائح تقنية يومية" (AI daily / smart devices / social / privacy)
- Replies:
  - replies to mentions only
  - strong anti-duplication + safety throttles + quiet hours + opt-out + kill-switch
- Dashboard + smart recommendation + optional email of recommendation (SMTP)

Required env/secrets:
  OPENROUTER_API_KEY
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
"""

import os
import re
import json
import time
import random
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

import tweepy
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(message)s")

STATE_FILE = "state.json"
AUDIT_LOG = "audit_log.jsonl"

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

# SMTP (optional)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
RECOMMENDATION_EMAIL_TO = os.getenv("RECOMMENDATION_EMAIL_TO", "")

# Poll Config (includes Daily Tech Tips)
POLL_CONFIG = {
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


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: str, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class TechBot:
    def __init__(self):
        self._require_env()

        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        self.x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )

        self.content_pillars = {
            "الذكاء الاصطناعي": "ملخصات موثوقة + أمثلة عملية",
            "الحوسبة السحابية": "مستجدات رسمية + تطبيق عملي",
            "البرمجة": "أفضل الممارسات + حلول عملية",
            "نصائح تقنية يومية": "نصائح عملية يومية في AI + الأجهزة الذكية + مواقع التواصل",
        }

        # RSS feeds per pillar
        self.feeds = {
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
                "https://apple.com/newsroom/rss-feed.rss",
                "https://about.fb.com/news/feed/",
                "https://instagram-engineering.com/feed",
            ],
        }

        self.system_instr = (
            "اكتب كمختص تقني عربي بأسلوب ودود وواضح.\n"
            "ممنوع اختلاق مصادر/روابط/إحصاءات/أرقام.\n"
            "التزم بالمصدر المُعطى فقط.\n"
            "كل تغريدة: Hook ثم Value ثم CTA (سؤال لطيف).\n"
            "لا تضع هاشتاقات داخل النص.\n"
            "لا تضع روابط إلا رابط المصدر مرة واحدة فقط في آخر تغريدة كسطر يبدأ بـ 'المصدر:'.\n"
        )

        self.state = self._load_state()
        logging.info("📌 Profile Checklist (يدوي): Bio واضح + Pin أفضل ثريد + Banner وعد قيمة")

    def _require_env(self):
        needed = ["OPENROUTER_API_KEY", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing = [k for k in needed if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

    # ---------- state ----------
    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
            except Exception:
                s = {}
        else:
            s = {}

        s.setdefault("used_links", [])
        s.setdefault("month_key", None)
        s.setdefault("posts_this_month", 0)
        s.setdefault("reads_this_month", 0)
        s.setdefault("post_times_15m", [])

        s.setdefault("last_poll_at", None)
        s.setdefault("last_poll_id", None)
        s.setdefault("last_poll_pillar", None)
        s.setdefault("last_poll_level", None)
        s.setdefault("last_poll_processed", False)
        s.setdefault("poll_pillar_index", 0)
        s.setdefault("poll_perf", {})

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

        return s

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _audit(self, event_type: str, payload: dict, content_type: str = None):
        append_jsonl(AUDIT_LOG, {
            "ts": utcnow_iso(),
            "type": event_type,
            "content_type": content_type,
            "payload": payload,
        })

    # ---------- guards ----------
    def _month_key(self):
        now = datetime.now(timezone.utc)
        return f"{now.year}-{now.month:02d}"

    def _ensure_month(self):
        mk = self._month_key()
        if self.state.get("month_key") != mk:
            self.state["month_key"] = mk
            self.state["posts_this_month"] = 0
            self.state["reads_this_month"] = 0
            self.state["post_times_15m"] = []
            self._save_state()

    def _can_post_monthly(self, n=1):
        self._ensure_month()
        return self.state["posts_this_month"] + n <= POST_CAP_MONTHLY

    def _mark_post_monthly(self, n=1):
        self._ensure_month()
        self.state["posts_this_month"] += n
        self._save_state()

    def _can_read_monthly(self, n=1):
        self._ensure_month()
        return self.state["reads_this_month"] + n <= READ_CAP_MONTHLY

    def _mark_read_monthly(self, n=1):
        self._ensure_month()
        self.state["reads_this_month"] += n
        self._save_state()

    def _prune_post_times_15m(self):
        self._ensure_month()
        now = time.time()
        w = now - 15 * 60
        self.state["post_times_15m"] = [t for t in self.state["post_times_15m"] if t >= w]
        self._save_state()

    def _can_post_15m(self, n=1):
        self._prune_post_times_15m()
        return len(self.state["post_times_15m"]) + n <= POSTS_PER_15MIN_SOFT

