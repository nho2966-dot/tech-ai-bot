# -*- coding: utf-8 -*-
"""
Tech AI Bot (X) — Production
- RSS threads + tips
- Daily Tech Tips pillar + Poll
- Topic of the Day: daily tip guided by last poll winner (if accessible)
- Mention replies with anti-dup + safety throttles
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
SOURCE_MODE = os.getenv("SOURCE_MODE", "1") == "1"    # نشر من مصادر RSS
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
QUIET_HOURS_UTC = os.getenv("QUIET_HOURS_UTC", "0-5")  # "0-5" => من منتصف الليل حتى 5 صباحًا UTC
AUTO_KILL_ON_ERRORS = os.getenv("AUTO_KILL_ON_ERRORS", "1") == "1"
MAX_ERRORS_PER_RUN = int(os.getenv("MAX_ERRORS_PER_RUN", "3"))
KILL_COOLDOWN_MINUTES = int(os.getenv("KILL_COOLDOWN_MINUTES", "180"))

LEVELS = ["beginner", "intermediate", "advanced"]

DEFAULT_HASHTAGS = ["#تقنية", "#برمجة"]
MAX_HASHTAGS = int(os.getenv("MAX_HASHTAGS", "2"))
SIGNATURE = os.getenv("SIGNATURE", "").strip()

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

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
