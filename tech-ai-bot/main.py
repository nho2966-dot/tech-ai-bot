# -*- coding: utf-8 -*-
"""Tech Expert Master Bot (X) — Basic Plan — Full Integrated (Final)

Features:
- Basic plan guards (monthly + 15-min soft)
- SOURCE_MODE: RSS-only content + Credibility Gate (no extra URLs, no unsupported numbers)
- Thread: numbering 1/N, hashtags only in last tweet (<=2), friendly CTA, readable line breaks
- First tweet: adds blurb ("نبذة:" + "مثال سريع:") and injects "حسب تصويتكم 👇" before "نبذة:" when driven by poll
- Poll Mode:
  - Per pillar polls (AI/Cloud/Programming)
  - Per audience level polls (beginner/intermediate/advanced) with attractive options
  - Auto-infer audience level from poll replies (proxy)
  - Measure poll engagement via public_metrics and learn best level (bandit-like)
- Dashboard + Smart Recommendation
- Optional: send recommendation email via SMTP

Required env:
OPENROUTER_API_KEY
X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET

Optional env:
DRY_RUN=1
SOURCE_MODE=1
POLL_MODE=1
TIP_MODE=1
SHOW_DASHBOARD=1
SEND_RECOMMENDATION=1
METRICS_DELAY_SECONDS=120
POST_CAP_MONTHLY=3000
READ_CAP_MONTHLY=15000
POSTS_PER_15MIN_SOFT=95
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, RECOMMENDATION_EMAIL_TO
"""

import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

import tweepy
from openai import OpenAI

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(message)s")

# ----------------------------
# Constants
# ----------------------------
TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
STATE_FILE = "state.json"
AUDIT_LOG = "audit_log.jsonl"

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
DIGIT_RE = re.compile(r"\d+")

# ----------------------------
# Basic plan guards
# ----------------------------
POST_CAP_MONTHLY = int(os.getenv("POST_CAP_MONTHLY", "3000"))
READ_CAP_MONTHLY = int(os.getenv("READ_CAP_MONTHLY", "15000"))
POSTS_PER_15MIN_SOFT = int(os.getenv("POSTS_PER_15MIN_SOFT", "95"))

# ----------------------------
# Modes
# ----------------------------
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
SOURCE_MODE = os.getenv("SOURCE_MODE", "1") == "1"
POLL_MODE = os.getenv("POLL_MODE", "1") == "1"
TIP_MODE = os.getenv("TIP_MODE", "1") == "1"
SHOW_DASHBOARD = os.getenv("SHOW_DASHBOARD", "0") == "1"
SEND_RECOMMENDATION = os.getenv("SEND_RECOMMENDATION", "0") == "1"

POLL_EVERY_DAYS = int(os.getenv("POLL_EVERY_DAYS", "7"))
POLL_DURATION_MINUTES = int(os.getenv("POLL_DURATION_MINUTES", "1440"))
METRICS_DELAY_SECONDS = int(os.getenv("METRICS_DELAY_SECONDS", "120"))

# ----------------------------
# Automation compliance
# ----------------------------
MAX_REPLIES_PER_RUN = int(os.getenv("MAX_REPLIES_PER_RUN", "3"))
BLOCK_TREND_JACKING = True

LEVELS = ["beginner", "intermediate", "advanced"]

# ----------------------------
# SMTP (optional)
# ----------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
RECOMMENDATION_EMAIL_TO = os.getenv("RECOMMENDATION_EMAIL_TO", "")

# ----------------------------
# Poll Config
# ----------------------------
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
}


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: str, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class TechBot:
    def __init__(self):
        self._require_env()

        self.signature = os.getenv("SIGNATURE", "").strip()
        self.max_hashtags = int(os.getenv("MAX_HASHTAGS", "2"))
        self.default_hashtags = ["#تقنية", "#برمجة"]

        self.content_pillars = {
            "الذكاء الاصطناعي": "ملخصات موثوقة + أمثلة عملية",
            "الحوسبة السحابية": "مستجدات رسمية + تطبيق عملي",
            "البرمجة": "أفضل الممارسات + حلول عملية",
        }

        self.feeds = {
            "الذكاء الاصطناعي": ["https://cloud.google.com/blog/rss", "https://blogs.microsoft.com/feed"],
            "الحوسبة السحابية": ["https://aws.amazon.com/about-aws/whats-new/recent/feed/", "https://cloud.google.com/blog/rss"],
            "البرمجة": ["https://devblogs.microsoft.com/dotnet/feed/", "https://devblogs.microsoft.com/visualstudio/feed/"],
        }

        self.system_instr = (
            "اكتب كمختص تقني عربي بأسلوب ودود وواضح.\n"
            "ممنوع اختلاق مصادر/روابط/إحصاءات/أرقام.\n"
            "التزم بالمصدر المُعطى فقط.\n"
            "كل تغريدة: Hook ثم Value ثم CTA (سؤال لطيف).\n"
            "لا تضع هاشتاقات داخل النص.\n"
            "لا تضع روابط إلا رابط المصدر مرة واحدة فقط في آخر تغريدة كسطر يبدأ بـ 'المصدر:'.\n"
        )

        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
        self.x = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )

        self.state = self._load_state()

        logging.info("📌 Profile Checklist (يدوي): Bio واضح + Pin أفضل ثريد + Banner وعد قيمة")

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

    # ----------------------------
    # Guards
    # ----------------------------
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

    def _can_post_15m(self, n=1):
        self._ensure_month()
        now = time.time()
        w = now - 15*60
        self.state["post_times_15m"] = [t for t in self.state["post_times_15m"] if t >= w]
        self._save_state()
        return len(self.state["post_times_15m"]) + n <= POSTS_PER_15MIN_SOFT

    def _mark_post_15m(self, n=1):
        now = time.time()
        self.state["post_times_15m"].extend([now] * n)
        self.state["post_times_15m"] = self.state["post_times_15m"][-400:]
        self._save_state()

    def _automation_guard(self, context: str) -> bool:
        if BLOCK_TREND_JACKING and ("ترند" in context or "trend" in context.lower()):
            logging.info("🛑 منع: ترند (Automation compliance).")
            return False
        return True

    # ----------------------------
    # Formatting & CTA
    # ----------------------------
    def _wrap_lines(self, text: str, max_len: int = 60) -> str:
        words = (text or "").split()
        if not words:
            return ""
        lines, cur = [], []
        cur_len = 0
        for w in words:
            add = len(w) + (1 if cur else 0)
            if cur_len + add > max_len:
                lines.append(" ".join(cur))
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += add
        if cur:
            lines.append(" ".join(cur))
        return "\n".join(lines)

    def _readability(self, text: str) -> str:
        parts = [p.strip() for p in (text or "").splitlines() if p.strip()]
        if not parts:
            return (text or "").strip()
        wrapped = [self._wrap_lines(p, 60) for p in parts]
        out = "\n".join(wrapped)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        return out

    def _smart_cta(self, pillar=None) -> str:
        pool = [
            "تحبها كخطوات ولا كقائمة أدوات؟",
            "قد واجهت المشكلة هذه؟ إيش كان أصعب جزء؟",
            "تحب مثال عملي على بيئتك؟",
            "أي خيار يناسب شغلك أكثر؟",
            "تبغاني أبسطها أكثر ولا كذا واضحة؟",
        ]
        return random.choice(pool)

    def _ensure_cta(self, text: str, pillar=None) -> str:
        if "؟" not in text and "?" not in text:
            return text.rstrip() + "\n" + self._smart_cta(pillar)
        return text

    # ----------------------------
    # Blurb + injection
    # ----------------------------
    def _make_blurb(self, title: str, summary: str) -> str:
        prompt = (
            "اكتب نبذة قصيرة جدًا (سطر واحد أو سطرين) تبدأ بـ 'نبذة:'\n"
            "وتحتوي 'مثال سريع:' يوضح الفكرة بمثال عملي صغير جدًا.\n"
            "بدون روابط، بدون هاشتاقات، بدون أرقام.\n"
            "لغة ودّية وواضحة.\n\n"
            f"العنوان: {title}\n"
            f"الملخص: {summary}\n"
        )
        resp = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[
                {"role": "system", "content": "سطر/سطرين فقط. بدون أرقام/روابط/هاشتاقات."},
                {"role": "user", "content": prompt},
            ],
        )
        blurb = resp.choices[0].message.content.strip()
        blurb = re.sub(URL_RE, "", blurb)
        blurb = re.sub(DIGIT_RE, "", blurb).strip()
        if not blurb.startswith("نبذة:"):
            blurb = "نبذة: " + blurb
        if "مثال" not in blurb:
            blurb = blurb.rstrip(" .") + " — مثال سريع: طبّقها على جزء صغير."
        if len(blurb) > 170:
            blurb = blurb[:169].rstrip() + "…"
        return blurb

    def _prepend_blurb(self, tweets, blurb: str, soft_limit=220):
        if not tweets:
            return tweets
        if "نبذة:" in tweets[0]:
            return tweets
        new_first = (tweets[0].strip() + "\n" + blurb).strip()
        if len(new_first) > soft_limit:
            new_first = new_first[:soft_limit - 1].rstrip() + "…"
        tweets[0] = new_first
        return tweets

    def _inject_poll_prefix(self, tweets):
        if not tweets:
            return tweets
        if "نبذة:" in tweets[0] and "حسب تصويتكم" not in tweets[0]:
            tweets[0] = re.sub(r"\nنبذة:", "\nحسب تصويتكم 👇\nنبذة:", tweets[0], count=1)
        return tweets

    # ----------------------------
    # RSS
    # ----------------------------
    def _fetch_url(self, url, timeout=12):
        req = Request(url, headers={"User-Agent": "TechExpertBot/1.0"})
        with urlopen(req, timeout=timeout) as r:
            return r.read()

    def _strip_html(self, s: str) -> str:
        s = re.sub(r"<[^>]+>", " ", s or "")
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s

    def _parse_feed(self, xml_bytes: bytes):
        items = []
        try:
            root = ET.fromstring(xml_bytes)
        except Exception:
            return items

        if "rss" in root.tag.lower():
            ch = root.find("channel")
            if ch is None:
                return items
            for it in ch.findall("item"):
                items.append({
                    "title": self._strip_html(it.findtext("title") or ""),
                    "link": (it.findtext("link") or "").strip(),
                    "summary": self._strip_html(it.findtext("description") or ""),
                })
            return items

        ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
        for e in root.findall(f"{ns}entry"):
            link = ""
            for l in e.findall(f"{ns}link"):
                if l.attrib.get("rel", "alternate") == "alternate":
                    link = l.attrib.get("href", "")
                    break
            items.append({
                "title": self._strip_html(e.findtext(f"{ns}title") or ""),
                "link": link.strip(),
                "summary": self._strip_html(e.findtext(f"{ns}summary") or e.findtext(f"{ns}content") or ""),
            })
        return items

    def _get_source_item(self, pillar: str, keyword: str = None):
        feeds = self.feeds.get(pillar, [])
        if not feeds:
            return None
        kw = (keyword or "").lower().strip()
        random.shuffle(feeds)
        for feed_url in feeds:
            try:
                items = self._parse_feed(self._fetch_url(feed_url))
                if kw:
                    for it in items[:50]:
                        blob = (it["title"] + " " + it["summary"]).lower()
                        if kw in blob and it["link"] and it["link"] not in self.state["used_links"]:
                            return it
                for it in items[:25]:
                    if it["link"] and it["link"] not in self.state["used_links"]:
                        return it
            except (HTTPError, URLError, TimeoutError):
                continue
            except Exception:
                continue
        return None

    # ----------------------------
    # Credibility gate
    # ----------------------------
    def _credibility_gate(self, tweets, source_link: str, source_text: str):
        joined = "\n".join(tweets)
        urls = URL_RE.findall(joined)
        for u in urls:
            if u.rstrip(").,]") != source_link:
                return False, f"رابط غير مسموح: {u}"
        if source_link not in joined:
            return False, "رابط المصدر غير موجود"
        out_nums = set(DIGIT_RE.findall(joined))
        src_nums = set(DIGIT_RE.findall(source_text or ""))
        if out_nums - src_nums:
            return False, "أرقام غير مدعومة بالمصدر"
        return True, "ok"

    # ----------------------------
    # Keyword seed
    # ----------------------------
    def _keyword_seed(self, pillar: str, level: str):
        try:
            cfg = POLL_CONFIG[pillar]["levels"][level]
            opt = cfg["options"][0]
            kws = cfg.get("keywords", {}).get(opt, [])
            return kws[0] if kws else None
        except Exception:
            return None

    # ----------------------------
    # Generate content
    # ----------------------------
    def _generate_thread(self, pillar: str, item: dict):
        prompt = (
            f"اكتب Thread عربي تقني عن: {pillar} اعتمادًا على المصدر فقط.\n"
            f"افصل بين التغريدات بهذا الفاصل حرفيًا: {THREAD_DELIM}\n"
            "شروط صارمة:\n"
            "- 2 إلى 5 تغريدات.\n"
            "- كل تغريدة <= 240 حرف.\n"
            "- لا روابط إلا رابط المصدر مرة واحدة في آخر تغريدة (المصدر: ...)\n"
            "- لا هاشتاقات.\n\n"
            f"العنوان: {item['title']}\n"
            f"الملخص: {item['summary']}\n"
            f"الرابط: {item['link']}\n"
        )
        resp = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip()
        parts = [p.strip() for p in raw.split(THREAD_DELIM) if p.strip()]
        if not parts:
            parts = [raw]
        parts = [self._readability(self._ensure_cta(p, pillar)) for p in parts]
        if item["link"] and item["link"] not in "\n".join(parts):
            parts[-1] = parts[-1].rstrip() + f"\nالمصدر: {item['link']}"
        return parts

    def _generate_tip(self, pillar: str, item: dict):
        prompt = (
            "اكتب تغريدة واحدة Tip عربية ودّية:\n"
            "- Hook + Tip + مثال سريع\n"
            "- سؤال لطيف\n"
            "- ضع (المصدر:) آخر سطر\n"
            "- لا أرقام/هاشتاقات\n\n"
            f"العنوان: {item['title']}\n"
            f"الملخص: {item['summary']}\n"
            f"الرابط: {item['link']}\n"
        )
        resp = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "system", "content": self.system_instr}, {"role": "user", "content": prompt}],
        )
        t = self._readability(self._ensure_cta(resp.choices[0].message.content.strip(), pillar))
        if item["link"] and item["link"] not in t:
            t = t.rstrip() + f"\nالمصدر: {item['link']}"
        t = re.sub(DIGIT_RE, "", t)
        return t[:240]

    # ----------------------------
    # Thread post-processing
    # ----------------------------
    def _add_numbering(self, tweets):
        n = len(tweets)
        if n <= 1:
            return [tweets[0][:TWEET_LIMIT]]
        out = []
        for i, t in enumerate(tweets, start=1):
            prefix = f"{i}/{n} "
            max_len = TWEET_LIMIT - len(prefix)
            t = t.strip()
            if len(t) > max_len:
                t = t[:max_len - 1].rstrip() + "…"
            out.append(prefix + t)
        return out

    def _apply_hashtags_last_only(self, tweets):
        tags = self.default_hashtags[: self.max_hashtags]
        tags = tags[:2]
        tag_line = " ".join(tags).strip()
        last = tweets[-1].rstrip() + f"\n\n{tag_line}"
        if self.signature:
            last = last.strip() + f" {self.signature}"
        tweets[-1] = last[:TWEET_LIMIT]
        return tweets

    # ----------------------------
    # Metrics (score)
    # ----------------------------
    def _score_tweet(self, tweet_id: str) -> int:
        if not tweet_id:
            return 0
        if not self._can_read_monthly(1):
            return 0
        try:
            tw = self.x.get_tweet(id=tweet_id, tweet_fields=["public_metrics"], user_auth=True)
            self._mark_read_monthly(1)
            m = tw.data.public_metrics
            likes = int(m.get("like_count", 0))
            replies = int(m.get("reply_count", 0))
            rts = int(m.get("retweet_count", 0))
            quotes = int(m.get("quote_count", 0))
            return replies * 3 + quotes * 3 + rts * 2 + likes
        except Exception:
            return 0

    # ----------------------------
    # Publish
    # ----------------------------
    def _publish_tweet(self, text: str, in_reply_to: str = None, content_type: str = None, pillar: str = None, level: str = None):
        if not self._can_post_monthly(1) or not self._can_post_15m(1):
            return None

        if DRY_RUN:
            logging.info(f"[DRY_RUN] Tweet:\n{text}\n")
            self._mark_post_monthly(1)
            self._mark_post_15m(1)
            tid = f"dry_{random.randint(1000,9999)}"
            self._audit("posted", {"pillar": pillar, "level": level, "score": 0, "tweet_id": tid}, content_type=content_type)
            return tid

        if in_reply_to:
            resp = self.x.create_tweet(text=text, in_reply_to_tweet_id=in_reply_to, user_auth=True)
        else:
            resp = self.x.create_tweet(text=text, user_auth=True)

        self._mark_post_monthly(1)
        self._mark_post_15m(1)
        tid = resp.data["id"]
        self._audit("posted", {"pillar": pillar, "level": level, "score": 0, "tweet_id": tid}, content_type=content_type)
        return tid

    def _publish_thread(self, tweets, pillar: str, level: str):
        needed = len(tweets)
        if not self._can_post_monthly(needed) or not self._can_post_15m(needed):
            return []
        prev = None
        ids = []
        for t in tweets:
            tid = self._publish_tweet(t, in_reply_to=prev, content_type="thread", pillar=pillar, level=level)
            if not tid:
                break
            prev = tid
            ids.append(tid)
            time.sleep(1.2)

        if ids and not DRY_RUN:
            time.sleep(max(0, METRICS_DELAY_SECONDS))
            sc = self._score_tweet(ids[0])
            self._audit("thread_scored", {"pillar": pillar, "level": level, "score": sc, "tweet_id": ids[0]}, content_type="thread")

        return ids

    # ----------------------------
    # Poll learning
    # ----------------------------
    def _init_perf_bucket(self, pillar: str):
        self.state.setdefault("poll_perf", {})
        self.state["poll_perf"].setdefault(pillar, {})
        for lvl in LEVELS:
            self.state["poll_perf"][pillar].setdefault(lvl, {"polls": 0, "eng_sum": 0, "reply_sum": 0})
        self._save_state()

    def _poll_has_ended(self) -> bool:
        last = self.state.get("last_poll_at")
        if not last:
            return False
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            return False
        return (datetime.now(timezone.utc) - last_dt).total_seconds() >= POLL_DURATION_MINUTES * 60

    def _classify_level_from_text(self, text: str) -> str:
        t = (text or "").lower()
        beginner_kw = ["وش يعني", "من وين أبدأ", "مبتدئ", "basics", "what is", "beginner"]
        advanced_kw = ["rag", "vector", "sre", "latency", "kubernetes", "orchestration", "scalability"]
        intermediate_kw = ["cost", "debug", "testing", "security", "performance", "refactor"]

        score = {"beginner": 0, "intermediate": 0, "advanced": 0}
        for k in beginner_kw:
            if k in t:
                score["beginner"] += 2
        for k in advanced_kw:
            if k in t:
                score["advanced"] += 2
        for k in intermediate_kw:
            if k in t:
                score["intermediate"] += 1

        best = max(score, key=lambda k: score[k])
        return best if score[best] else "intermediate"

    def _infer_level_from_poll_replies(self, poll_id: str) -> str:
        if not self._can_read_monthly(1):
            return "intermediate"
        try:
            query = f"conversation_id:{poll_id} -is:retweet"
            res = self.x.search_recent_tweets(query=query, max_results=50, user_auth=True)
            self._mark_read_monthly(1)
            if not res or not res.data:
                return "intermediate"
            votes = {"beginner": 0, "intermediate": 0, "advanced": 0}
            for tw in res.data:
                votes[self._classify_level_from_text(tw.text)] += 1
            best = max(votes, key=lambda k: votes[k])
            return best if votes[best] else "intermediate"
        except Exception:
            return "intermediate"

    def _update_poll_learning(self):
        if not self._poll_has_ended() or self.state.get("last_poll_processed"):
            return
        poll_id = self.state.get("last_poll_id")
        pillar = self.state.get("last_poll_pillar")
        used_level = self.state.get("last_poll_level")
        if not poll_id or not pillar or not used_level:
            return

        self._init_perf_bucket(pillar)
        inferred = self._infer_level_from_poll_replies(poll_id)
        score = self._score_tweet(poll_id)

        self.state["poll_perf"][pillar][used_level]["polls"] += 1
        self.state["poll_perf"][pillar][used_level]["eng_sum"] += score
        self.state["poll_perf"][pillar][inferred]["reply_sum"] += 1

        self.state["last_poll_processed"] = True
        self._save_state()
        self._audit("poll_learned", {"pillar": pillar, "level": used_level, "score": score, "tweet_id": poll_id}, content_type="poll")

    def _choose_level_for_pillar(self, pillar: str) -> str:
        self._init_perf_bucket(pillar)
        perf = self.state["poll_perf"][pillar]
        avgs = {lvl: perf[lvl]["eng_sum"] / max(1, perf[lvl]["polls"]) for lvl in LEVELS}
        best = max(avgs, key=lambda k: avgs[k])
        reply_pref = max(LEVELS, key=lambda k: perf[k]["reply_sum"])
        r = random.random()
        if r < 0.70:
            return best
        elif r < 0.90:
            return reply_pref
        return random.choice(LEVELS)

    # ----------------------------
    # Poll posting
    # ----------------------------
    def _should_run_poll(self) -> bool:
        if not POLL_MODE:
            return False
        last = self.state.get("last_poll_at")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            return True
        return (datetime.now(timezone.utc) - last_dt).days >= POLL_EVERY_DAYS

    def _pick_poll_pillar(self) -> str:
        pillars = list(POLL_CONFIG.keys())
        idx = int(self.state.get("poll_pillar_index", 0)) % len(pillars)
        pillar = pillars[idx]
        self.state["poll_pillar_index"] = (idx + 1) % len(pillars)
        self._save_state()
        return pillar

    def _post_poll(self):
        if not self._automation_guard("poll"):
            return None
        pillar = self._pick_poll_pillar()
        level = self._choose_level_for_pillar(pillar)
        cfg = POLL_CONFIG[pillar]["levels"][level]
        question = POLL_CONFIG[pillar]["question"]
        options = cfg["options"][:4]

        if not self._can_post_monthly(1) or not self._can_post_15m(1):
            return None

        if DRY_RUN:
            logging.info(f"[DRY_RUN] Poll {pillar}/{level}: {question} | {options}")
            poll_id = f"dry_poll_{random.randint(1000,9999)}"
        else:
            resp = self.x.create_tweet(text=question, poll_options=options, poll_duration_minutes=POLL_DURATION_MINUTES, user_auth=True)
            poll_id = resp.data["id"]
            self._mark_post_monthly(1)
            self._mark_post_15m(1)

        self.state["last_poll_at"] = utcnow_iso()
        self.state["last_poll_id"] = poll_id
        self.state["last_poll_pillar"] = pillar
        self.state["last_poll_level"] = level
        self.state["last_poll_processed"] = False
        self._save_state()

        self._audit("poll_posted", {"pillar": pillar, "level": level, "score": 0, "tweet_id": poll_id}, content_type="poll")
        return poll_id

    # ----------------------------
    # Dashboard & recommendation
    # ----------------------------
    def _smart_recommendation(self, days: int = 14):
        if not os.path.exists(AUDIT_LOG):
            return None
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        pillar_scores, level_scores, type_scores = {}, {}, {}
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                ts = datetime.fromisoformat(r["ts"]).timestamp()
                if ts < cutoff:
                    continue
                payload = r.get("payload", {})
                score = int(payload.get("score", 0))
                pillar = payload.get("pillar")
                level = payload.get("level")
                ctype = r.get("content_type")
                if pillar:
                    pillar_scores.setdefault(pillar, []).append(score)
                if level:
                    level_scores.setdefault(level, []).append(score)
                if ctype:
                    type_scores.setdefault(ctype, []).append(score)

        def best_avg(d):
            if not d:
                return None
            return max(d.items(), key=lambda x: sum(x[1]) / max(1, len(x[1])))[0]

        return {
            "pillar": best_avg(pillar_scores),
            "level": best_avg(level_scores),
            "content_type": best_avg(type_scores),
            "days": days,
        }

    def show_dashboard(self, days: int = 30):
        print(f"\n📊 DASHBOARD (آخر {days} يوم)")
        print(f"- posts_this_month: {self.state.get('posts_this_month')}")
        print(f"- reads_this_month: {self.state.get('reads_this_month')}")
        print(f"- last_poll_pillar: {self.state.get('last_poll_pillar')}")
        print(f"- last_poll_level: {self.state.get('last_poll_level')}")
        reco = self._smart_recommendation(days=14)
        if reco and any(reco.values()):
            print("\n🧠 توصية ذكية:")
            print(f"- المحور: {reco.get('pillar')}")
            print(f"- المستوى: {reco.get('level')}")
            print(f"- النوع: {reco.get('content_type')}")

    def send_recommendation_email(self, days: int = 14):
        if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM and RECOMMENDATION_EMAIL_TO):
            logging.info("📭 SMTP غير مكتمل — تم تجاوز الإرسال.")
            return
        reco = self._smart_recommendation(days=days) or {}
        pillar = reco.get("pillar") or "الذكاء الاصطناعي"
        level = reco.get("level") or "intermediate"
        ctype = reco.get("content_type") or "thread"
        subject = "🧠 توصية المحتوى الذكية – الأسبوع القادم"
        body = f"""مرحبًا 👋

بناءً على تحليل آخر {days} يوم:

✅ المحور الأقوى: {pillar}
✅ مستوى الجمهور الأنسب: {level}
✅ نوع المحتوى الأفضل: {ctype}

📌 الاقتراح:
انشر {ctype} عن "{pillar}" موجّه لمستوى "{level}".

— Tech Bot
"""
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["From"] = SMTP_FROM
        msg["To"] = RECOMMENDATION_EMAIL_TO
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
            self._audit("email_sent", {"to": RECOMMENDATION_EMAIL_TO, "score": 0}, content_type="email")
            logging.info("📨 تم إرسال التوصية بالبريد.")
        except Exception as e:
            self._audit("email_failed", {"error": str(e), "score": 0}, content_type="email")
            logging.error(f"❌ فشل إرسال البريد: {e}")

    # ----------------------------
    # Content mode
    # ----------------------------
    def _content_mode(self) -> str:
        if POLL_MODE and self._should_run_poll():
            return "poll"
        if TIP_MODE:
            wd = datetime.now(timezone.utc).weekday()
            if wd in (1, 3):
                return "tip"
        return "thread"

    # ----------------------------
    # Run
    # ----------------------------
    def run(self):
        self._update_poll_learning()

        if SHOW_DASHBOARD:
            self.show_dashboard(days=30)
            return

        if SEND_RECOMMENDATION:
            self.send_recommendation_email(days=14)
            return

        mode = self._content_mode()
        if mode == "poll":
            self._post_poll()
            return

        pillar = self.state.get("last_poll_pillar") or random.choice(list(self.content_pillars.keys()))
        level = self.state.get("last_poll_level") or "intermediate"
        keyword = self._keyword_seed(pillar, level)

        item = self._get_source_item(pillar, keyword=keyword) if SOURCE_MODE else None
        if not item:
            logging.info("⚠️ لا يوجد عنصر RSS مناسب.")
            return

        source_link = item["link"]
        source_text = (item["title"] + " " + item["summary"]).strip()

        if mode == "tip":
            tip = self._generate_tip(pillar, item)
            ok, _ = self._credibility_gate([tip], source_link, source_text)
            if not ok:
                logging.info("🛑 Tip blocked by credibility gate")
                return
            tags = " ".join(self.default_hashtags[:2])
            tip_final = (tip.strip() + f"\n\n{tags}").strip()[:TWEET_LIMIT]
            tid = self._publish_tweet(tip_final, content_type="tip", pillar=pillar, level=level)
            if tid and not DRY_RUN:
                time.sleep(max(0, METRICS_DELAY_SECONDS))
                sc = self._score_tweet(tid)
                self._audit("tip_scored", {"pillar": pillar, "level": level, "score": sc, "tweet_id": tid}, content_type="tip")
            self.state["used_links"].append(source_link)
            self.state["used_links"] = self.state["used_links"][-200:]
            self._save_state()
            return

        tweets = self._generate_thread(pillar, item)
        ok, _ = self._credibility_gate(tweets, source_link, source_text)
        if not ok:
            logging.info("🛑 Thread blocked by credibility gate")
            return

        blurb = self._make_blurb(item["title"], item["summary"])
        tweets = self._prepend_blurb(tweets, blurb, soft_limit=220)

        if self.state.get("last_poll_id"):
            tweets = self._inject_poll_prefix(tweets)

        tweets = [self._readability(t) for t in tweets]
        tweets = self._add_numbering(tweets)
        tweets = self._apply_hashtags_last_only(tweets)

        self._publish_thread(tweets, pillar=pillar, level=level)

        self.state["used_links"].append(source_link)
        self.state["used_links"] = self.state["used_links"][-200:]
        self._save_state()


if __name__ == "__main__":
    TechBot().run()
