# -*- coding: utf-8 -*-

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

# =========================
# Logging
# =========================
logging.basicConfig(level=logging.INFO, format="%(message)s")

# =========================
# Constants
# =========================
TWEET_LIMIT = 280
THREAD_DELIM = "\n---\n"
STATE_FILE = "state.json"
AUDIT_LOG = "audit_log.jsonl"

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
DIGIT_RE = re.compile(r"\d+")
HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)

# =========================
# X Developer Platform — Basic Guards
# =========================
POST_CAP_MONTHLY = int(os.getenv("POST_CAP_MONTHLY", "3000"))
READ_CAP_MONTHLY = int(os.getenv("READ_CAP_MONTHLY", "15000"))
POSTS_PER_15MIN_SOFT = int(os.getenv("POSTS_PER_15MIN_SOFT", "95"))

# =========================
# Modes
# =========================
SOURCE_MODE = os.getenv("SOURCE_MODE", "1") == "1"
POLL_MODE = os.getenv("POLL_MODE", "1") == "1"
TIP_MODE = os.getenv("TIP_MODE", "1") == "1"

POLL_EVERY_DAYS = int(os.getenv("POLL_EVERY_DAYS", "7"))
POLL_DURATION_MINUTES = int(os.getenv("POLL_DURATION_MINUTES", "1440"))  # 24h

SHOW_DASHBOARD = os.getenv("SHOW_DASHBOARD", "0") == "1"
SEND_RECOMMENDATION = os.getenv("SEND_RECOMMENDATION", "0") == "1"

# =========================
# Automation Compliance switches
# =========================
AUTO_REPLY_MENTIONS_ONLY = True
MAX_REPLIES_PER_RUN = int(os.getenv("MAX_REPLIES_PER_RUN", "3"))
BLOCK_TREND_JACKING = True

# =========================
# Audience levels
# =========================
LEVELS = ["beginner", "intermediate", "advanced"]

# =========================
# Email (SMTP) optional
# =========================
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
RECOMMENDATION_EMAIL_TO = os.getenv("RECOMMENDATION_EMAIL_TO", "")

# =========================
# Poll config (per pillar + per level + جذابة)
# =========================
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


class TechExpertMaster:
    def __init__(self):
        logging.info("--- Tech Expert Master | Basic FULL (Fixed) ---")

        self.DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
        self.SIGNATURE = os.getenv("SIGNATURE", "").strip()
        self.MAX_HASHTAGS = int(os.getenv("MAX_HASHTAGS", "2"))
        self.DEFAULT_HASHTAGS = ["#تقنية", "#برمجة"]

        required = ["OPENROUTER_API_KEY", "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        self.client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        self.content_pillars = {
            "الذكاء الاصطناعي": "ملخصات موثوقة + أمثلة عملية",
            "الحوسبة السحابية": "مستجدات رسمية + تطبيق عملي",
            "البرمجة": "أفضل الممارسات + حلول عملية",
        }

        self.FEEDS = {
            "الذكاء الاصطناعي": ["https://cloud.google.com/blog/rss", "https://blogs.microsoft.com/feed"],
            "الحوسبة السحابية": ["https://aws.amazon.com/about-aws/whats-new/recent/feed/", "https://cloud.google.com/blog/rss"],
            "البرمجة": ["https://devblogs.microsoft.com/dotnet/feed/", "https://devblogs.microsoft.com/visualstudio/feed/"],
        }

        self.system_instr = (
            "اكتب كمختص تقني عربي بأسلوب ودود وواضح.\n"
            "ممنوع اختلاق مصادر/روابط/إحصاءات/أرقام.\n"
            "التزم بالمصدر المُعطى فقط.\n"
            "كل تغريدة: Hook ثم Value ثم CTA.\n"
            "لا تضع هاشتاقات داخل النص.\n"
            "لا تضع روابط إلا رابط المصدر مرة واحدة فقط بآخر تغريدة كسطر يبدأ بـ 'المصدر:'.\n"
        )

        self.state = self._load_state()

        logging.info("📌 Profile Checklist (يدوي): Bio واضح + Pin أفضل ثريد + Banner وعد قيمة")

    # -------------------------
    # State & Audit
    # -------------------------
    def _load_state(self):
        s = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
            except Exception:
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
        s.setdefault("poll_perf", {})  # pillar->level->stats

        return s

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _audit(self, event_type, payload, content_type=None):
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "content_type": content_type,
            "payload": payload
        }
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # -------------------------
    # Guards
    # -------------------------
    def _month_key(self):
        now = datetime.now(timezone.utc)
        return f"{now.year}-{now.month:02d}"

    def _ensure_month_bucket(self):
        mk = self._month_key()
        if self.state.get("month_key") != mk:
            self.state["month_key"] = mk
            self.state["posts_this_month"] = 0
            self.state["reads_this_month"] = 0
            self.state["post_times_15m"] = []
            self._save_state()

    def _can_post_monthly(self, n=1):
        self._ensure_month_bucket()
        return self.state["posts_this_month"] + n <= POST_CAP_MONTHLY

    def _mark_posted_monthly(self, n=1):
        self._ensure_month_bucket()
        self.state["posts_this_month"] += n
        self._save_state()

    def _can_read_monthly(self, n=1):
        self._ensure_month_bucket()
        return self.state["reads_this_month"] + n <= READ_CAP_MONTHLY

    def _mark_read_monthly(self, n=1):
        self._ensure_month_bucket()
        self.state["reads_this_month"] += n
        self._save_state()

    def _can_post_15m(self, n=1):
        self._ensure_month_bucket()
        now = time.time()
        window_start = now - 15 * 60
        self.state["post_times_15m"] = [t for t in self.state["post_times_15m"] if t >= window_start]
        self._save_state()
        return len(self.state["post_times_15m"]) + n <= POSTS_PER_15MIN_SOFT

    def _mark_post_15m(self, n=1):
        now = time.time()
        self.state["post_times_15m"].extend([now] * n)
        self.state["post_times_15m"] = self.state["post_times_15m"][-400:]
        self._save_state()

    def _automation_compliance_guard(self, context: str) -> bool:
        if BLOCK_TREND_JACKING and ("ترند" in context or "trend" in context.lower()):
            logging.info("🛑 منع: ترند (Automation compliance).")
            return False
        return True

    # -------------------------
    # Formatting & CTA
    # -------------------------
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

    def _enforce_readability(self, text: str) -> str:
        parts = [p.strip() for p in (text or "").splitlines() if p.strip()]
        if not parts:
            return text.strip()
        wrapped = [self._wrap_lines(p, 60) for p in parts]
        out = "\n".join(wrapped)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        return out

    def _smart_cta(self, pillar=None):
        pool = [
            "تحبها كخطوات ولا كقائمة أدوات؟",
            "قد واجهت المشكلة هذه؟ إيش كان أصعب جزء؟",
            "تحب مثال عملي على بيئتك؟",
            "أي خيار يناسب شغلك أكثر؟",
        ]
        return random.choice(pool)

    def _ensure_cta(self, text: str, pillar=None) -> str:
        if "؟" not in text and "?" not in text:
            return text.rstrip() + "\n" + self._smart_cta(pillar)
        return text

    # -------------------------
    # Blurb + injection
    # -------------------------
    def _make_blurb(self, title: str, summary: str) -> str:
        prompt = (
            "اكتب نبذة قصيرة جدًا تبدأ بـ 'نبذة:' وتتضمن 'مثال سريع:'.\n"
            "بدون روابط/هاشتاقات/أرقام.\n\n"
            f"العنوان: {title}\n"
            f"الملخص: {summary}\n"
        )
        resp = self.ai_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "system", "content": "سطر/سطرين فقط."},
                      {"role": "user", "content": prompt}]
        )
        blurb = resp.choices[0].message.content.strip()
        blurb = re.sub(URL_RE, "", blurb)
        blurb = re.sub(DIGIT_RE, "", blurb).strip()
        if not blurb.startswith("نبذة:"):
            blurb = "نبذة: " + blurb
        if "مثال" not in blurb:
            blurb = blurb.rstrip(" .") + " — مثال سريع: طبّقها على جزء صغير."
        return blurb

    def _prepend_blurb_to_first_tweet(self, tweets, blurb: str, soft_limit=220):
        if not tweets:
            return tweets
        if "نبذة:" in tweets[0]:
            return tweets
        new_first = (tweets[0].strip() + "\n" + blurb).strip()
        if len(new_first) > soft_limit:
            new_first = new_first[:soft_limit - 1].rstrip() + "…"
        tweets[0] = new_first
        return tweets

    def _inject_poll_prefix_before_blurb(self, tweets):
        if not tweets:
            return tweets
        if "نبذة:" in tweets[0] and "حسب تصويتكم" not in tweets[0]:
            tweets[0] = re.sub(r"\nنبذة:", "\nحسب تصويتكم 👇\nنبذة:", tweets[0], count=1)
        return tweets

    # -------------------------
    # RSS parsing
    # -------------------------
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
        else:
            ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
            for e in root.findall(f"{ns}entry"):
                link = ""
                for l in e.findall(f"{ns}link"):
                    if l.attrib.get("rel", "alternate") == "alternate":
                        link = l.attrib.get("href", "")
                items.append({
                    "title": self._strip_html(e.findtext(f"{ns}title") or ""),
                    "link": link.strip(),
                    "summary": self._strip_html(e.findtext(f"{ns}summary") or e.findtext(f"{ns}content") or ""),
                })
        return items

    def _get_source_item(self, pillar: str, keyword: str = None):
        feeds = self.FEEDS.get(pillar, [])
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
            except Exception:
                continue
        return None

    # -------------------------
    # Credibility Gate
    # -------------------------
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

    # -------------------------
    # Thread helpers
    # -------------------------
    def _add_numbering_prefix(self, tweets):
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

    def _apply_hashtags_to_last_tweet(self, tweets):
        tags = self.DEFAULT_HASHTAGS[: self.MAX_HASHTAGS]
        tag_line = " ".join(tags).strip()
        last = (tweets[-1].rstrip() + f"\n\n{tag_line}").strip()
        if self.SIGNATURE:
            last = (last + f" {self.SIGNATURE}").strip()
        tweets[-1] = last[:TWEET_LIMIT]
        return tweets

    # -------------------------
    # Poll learning (adaptive)
    # -------------------------
    def _init_perf_bucket(self, pillar):
        self.state["poll_perf"].setdefault(pillar, {})
        for lvl in LEVELS:
