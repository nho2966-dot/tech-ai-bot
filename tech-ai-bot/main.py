# -*- coding: utf-8 -*-
"""
Tech Expert Master Bot (X) — Basic Plan — FULL Integrated Version
Features:
- Basic plan guards (monthly + 15-min soft)
- SOURCE_MODE: RSS-only content + Credibility Gate
- Threads with numbering, hashtags only in last tweet (<=2)
- Friendly tone + readable formatting + CTA magnet
- Blurb + practical example in first tweet + "حسب تصويتكم 👇" injection before "نبذة:"
- Poll Mode:
  - per pillar polls
  - per audience level polls (beginner/intermediate/advanced)
  - attractive options (pain/outcome-based)
  - infer level from replies (proxy)
  - measure engagement via public_metrics
  - store performance & bias toward best level (bandit-like)
- Dashboard CLI + Smart Recommendation
- Email recommendation via SMTP (optional)
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

HASHTAG_RE = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
DIGIT_RE = re.compile(r"\d+")


# =========================
# X Developer Platform — Basic guards (from plan table)
# =========================
POST_CAP_MONTHLY = int(os.getenv("POST_CAP_MONTHLY", "3000"))     # user-level posts/month
READ_CAP_MONTHLY = int(os.getenv("READ_CAP_MONTHLY", "15000"))    # app-level reads/month
POSTS_PER_15MIN_SOFT = int(os.getenv("POSTS_PER_15MIN_SOFT", "95"))  # POST /2/tweets per-user is limited; keep soft < 100


# =========================
# Automation Compliance switches
# =========================
AUTO_REPLY_MENTIONS_ONLY = True
MAX_REPLIES_PER_RUN = int(os.getenv("MAX_REPLIES_PER_RUN", "3"))
BLOCK_TREND_JACKING = True  # don't auto-post about trending topics


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
EMAIL_RECO_WEEKDAY_UTC = int(os.getenv("EMAIL_RECO_WEEKDAY_UTC", "6"))  # 6=Sunday


# =========================
# Audience levels
# =========================
LEVELS = ["beginner", "intermediate", "advanced"]


# =========================
# Poll Config (Per Pillar + Per Level + Attractive options)
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


# =========================
# SMTP Email config (optional)
# =========================
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
RECOMMENDATION_EMAIL_TO = os.getenv("RECOMMENDATION_EMAIL_TO", "")


class TechExpertMasterBasicFull:
    def __init__(self):
        logging.info("--- Tech Expert Master | Basic FULL ---")

        # DRY_RUN
        self.DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

        # hashtags policy
        self.MAX_HASHTAGS = int(os.getenv("MAX_HASHTAGS", "2"))
        self.DEFAULT_HASHTAGS = ["#تقنية", "#برمجة"]

        # signature optional
        self.SIGNATURE = os.getenv("SIGNATURE", "").strip()

        # Required keys
        required = [
            "OPENROUTER_API_KEY",
            "X_API_KEY", "X_API_SECRET",
            "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
        ]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

        # OpenRouter client
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        # Tweepy client
        self.client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # Content pillars
        self.content_pillars = {
            "الذكاء الاصطناعي": "ملخصات موثوقة + أمثلة عملية",
            "الحوسبة السحابية": "مستجدات رسمية + تطبيق عملي",
            "البرمجة": "أفضل الممارسات + حلول عملية",
        }

        # RSS feeds
        self.FEEDS = {
            "الذكاء الاصطناعي": [
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
        }

        # System instruction: friendly + credibility
        self.system_instr = (
            "اكتب كمختص تقني عربي بأسلوب ودود وواضح.\n"
            "ممنوع اختلاق مصادر/روابط/إحصاءات/أرقام.\n"
            "التزم بالمصدر المُعطى فقط.\n"
            "التنسيق: أسطر قصيرة، فكرة واحدة لكل تغريدة.\n"
            "كل تغريدة: Hook ثم Value ثم CTA (سؤال لطيف).\n"
            "لا تضع هاشتاقات داخل النص.\n"
            "لا تضع روابط إلا رابط المصدر مرة واحدة فقط في آخر تغريدة كسطر يبدأ بـ 'المصدر:'.\n"
        )

        # Keywords to decide replies (mentions only)
        self.TECH_TRIGGERS = [
            "كيف", "لماذا", "ما", "وش", "أفضل", "شرح", "حل", "مشكلة", "خطأ",
            "error", "bug", "issue", "api", "python", "javascript", "rust",
            "ai", "security", "cloud", "aws", "azure", "gcp"
        ]

        # Profile checklist reminder (human action)
        logging.info("📌 Profile Checklist (Manual):")
        logging.info("• Bio: Threads تقنية مبنية على مصادر رسمية + أمثلة عملية")
        logging.info("• Pin Tweet: أفضل ثريد/تعريف بالقيمة + قائمة مصادر")
        logging.info("• Banner: وعد قيمة واضح (ملخصات موثوقة + أمثلة عملية)")

        self.state = self._load_state()

    # =========================================================
    # State + Audit
    # =========================================================
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

        # month guards
        s.setdefault("month_key", None)
        s.setdefault("posts_this_month", 0)
        s.setdefault("reads_this_month", 0)
        s.setdefault("post_times_15m", [])

        # mentions
        s.setdefault("last_mention_id", None)

        # polls
        s.setdefault("last_poll_at", None)
        s.setdefault("last_poll_id", None)
        s.setdefault("last_poll_pillar", None)
        s.setdefault("last_poll_level", None)
        s.setdefault("last_poll_processed", False)
        s.setdefault("poll_pillar_index", 0)
        s.setdefault("poll_perf", {})  # pillar -> level -> stats

        return s

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _audit(self, event_type: str, payload: dict, content_type: str = None):
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "content_type": content_type or payload.get("content_type"),
            "payload": payload
        }
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # =========================================================
    # Guards
    # =========================================================
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

    def _sleep_jitter(self, base=1.2, spread=2.0):
        time.sleep(base + random.random() * spread)

    # =========================================================
    # Automation compliance guard (simple)
    # =========================================================
    def _automation_compliance_guard(self, context: str) -> bool:
        if BLOCK_TREND_JACKING and ("trend" in context.lower() or "ترند" in context):
            logging.info("🛑 منع: ترند (Automation Rules safety).")
            return False
        return True

    # =========================================================
    # Formatting (Shareability): short lines, 1 idea, breaks
    # =========================================================
    def _wrap_lines(self, text: str, max_len: int = 60) -> str:
        """
        Simple word wrap to max_len chars per line (best effort for Arabic/English).
        """
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
        """
        - breaks paragraphs
        - wraps lines
        - avoids huge blocks
        """
        parts = [p.strip() for p in (text or "").split("\n") if p.strip()]
        if not parts:
            return text.strip()
        wrapped = [self._wrap_lines(p, max_len=60) for p in parts]
        # keep it visually scannable
        out = "\n".join(wrapped)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        return out

    # =========================================================
    # Hashtag policy: <=2, last tweet only
    # =========================================================
    def _enforce_hashtag_policy(self, tags):
        return tags[:2]

    # =========================================================
    # CTA (friendly magnets)
    # =========================================================
    def _smart_cta(self, pillar=None):
        pool = [
            "تحبها كخطوات ولا كقائمة أدوات؟",
            "قد واجهت الشي هذا؟ إيش كان أصعب جزء؟",
            "تحب مثال عملي على بيئتك؟",
            "أي خيار يناسب شغلك أكثر؟",
            "تبغاني أبسطها أكثر ولا كذا واضحة؟",
        ]
        # light personalization
        if pillar == "الحوسبة السحابية":
            pool.append("تبغى مثال AWS ولا Azure ولا GCP؟")
        if pillar == "البرمجة":
            pool.append("تفضل مثال Python ولا .NET؟")
        if pillar == "الذكاء الاصطناعي":
            pool.append("تبغى مثال Prompt ولا RAG؟")
        return random.choice(pool)

    def _ensure_cta(self, text: str, pillar=None) -> str:
        if "؟" not in text and "?" not in text:
            return text.rstrip() + "\n" + self._smart_cta(pillar)
        return text

    # =========================================================
    # Blurb with practical example
    # =========================================================
    def _make_blurb(self, title: str, summary: str) -> str:
        prompt = (
            "اكتب نبذة قصيرة جدًا (سطر واحد أو سطرين) تبدأ بـ 'نبذة:'\n"
            "وتحتوي 'مثال سريع:' يوضح الفكرة بمثال عملي صغير جدًا.\n"
            "بدون روابط، بدون هاشتاقات، بدون أرقام.\n"
            "لغة ودّية وواضحة.\n\n"
            f"العنوان: {title}\n"
            f"الملخص: {summary}\n"
        )

        resp = self.ai_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[
                {"role": "system", "content": "سطر/سطرين فقط. بدون أرقام/روابط/هاشتاقات."},
                {"role": "user", "content": prompt}
            ]
        )
        blurb = resp.choices[0].message.content.strip()
        blurb = re.sub(URL_RE, "", blurb)
        blurb = re.sub(HASHTAG_RE, "", blurb)
        blurb = re.sub(DIGIT_RE, "", blurb).strip()

        if not blurb.startswith("نبذة:"):
            blurb = "نبذة: " + blurb
        if "مثال" not in blurb:
            blurb = blurb.rstrip(" .") + " — مثال سريع: طبّق الفكرة على جزء صغير أولًا."

        if len(blurb) > 170:
            blurb = blurb[:169].rstrip() + "…"
        return blurb

    def _prepend_blurb_to_first_tweet(self, tweets, blurb: str, soft_limit=220):
        if not tweets:
            return tweets
        first = tweets[0].strip()
        if "نبذة:" in first:
            return tweets

        lines = [l.strip() for l in first.splitlines() if l.strip()]
        hook = lines[0] if lines else first
        rest = "\n".join(lines[1:]).strip()

        new_first = f"{hook}\n{blurb}"
        if rest:
            new_first += f"\n{rest}"

        if len(new_first) > soft_limit:
            new_first = new_first[:soft_limit - 1].rstrip() + "…"

        tweets[0] = new_first
        return tweets

    def _inject_poll_prefix_before_blurb(self, tweets):
        """
        Inject 'حسب تصويتكم 👇' before 'نبذة:' in first tweet (if present).
        """
        if not tweets:
            return tweets
        if "نبذة:" in tweets[0] and "حسب تصويتكم" not in tweets[0]:
            tweets[0] = re.sub(r"\nنبذة:", "\nحسب تصويتكم 👇\nنبذة:", tweets[0], count=1)
        return tweets

    # =========================================================
    # RSS fetch + parse
    # =========================================================
    def _fetch_url(self, url, timeout=12):
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TechExpertBot/1.0)"}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()

    def _strip_html(self, s: str) -> str:
        if not s:
            return ""
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s

    def _parse_feed(self, xml_bytes: bytes):
        items = []
        try:
            root = ET.fromstring(xml_bytes)
        except Exception:
            return items

        tag = root.tag.lower()

        if "rss" in tag:
            channel = root.find("channel")
            if channel is None:
                return items
            for it in channel.findall("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                desc = (it.findtext("description") or "").strip()
                items.append({
                    "title": self._strip_html(title),
                    "link": link,
                    "summary": self._strip_html(desc)
                })
            return items

        if "feed" in tag:
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"
            for entry in root.findall(f"{ns}entry"):
                title = (entry.findtext(f"{ns}title") or "").strip()
                summary = (entry.findtext(f"{ns}summary") or entry.findtext(f"{ns}content") or "").strip()
                link = ""
                for l in entry.findall(f"{ns}link"):
                    rel = l.attrib.get("rel", "alternate")
                    if rel == "alternate" and l.attrib.get("href"):
                        link = l.attrib["href"]
                        break
                items.append({
                    "title": self._strip_html(title),
                    "link": link.strip(),
                    "summary": self._strip_html(summary)
                })
            return items

        return items

    def _get_source_item(self, pillar: str, keyword: str = None):
        feeds = self.FEEDS.get(pillar, [])
        if not feeds:
            return None

        keyword_l = (keyword or "").lower().strip()

        random.shuffle(feeds)
        for feed_url in feeds:
            try:
                xml_bytes = self._fetch_url(feed_url)
                items = self._parse_feed(xml_bytes)

                # Prefer keyword match if provided
                if keyword_l:
                    for it in items[:50]:
                        blob = (it.get("title", "") + " " + it.get("summary", "")).lower()
                        if keyword_l in blob and it.get("link") and it["link"] not in self.state["used_links"]:
                            return it

                # fallback to first unused
                for it in items[:25]:
                    if it.get("link") and it["link"] not in self.state["used_links"]:
                        return it

            except (HTTPError, URLError, TimeoutError):
                continue
            except Exception:
                continue

        return None

    # =========================================================
    # Credibility gate
    # =========================================================
    def _credibility_gate(self, tweets, source_link: str, source_text: str):
        joined = "\n".join(tweets)

        # Only allow source link
        urls = URL_RE.findall(joined)
        allowed = {source_link}
        for u in urls:
            uu = u.rstrip(").,]")
            if uu not in allowed:
                return False, f"رابط غير مسموح: {u}"

        # Must include source link at least once
        if source_link not in joined:
            return False, "رابط المصدر غير موجود"

        # numbers must exist in source text
        out_nums = set(DIGIT_RE.findall(joined))
        src_nums = set(DIGIT_RE.findall(source_text or ""))
        extra = out_nums - src_nums
        if extra:
            return False, f"أرقام غير مدعومة بالمصدر: {sorted(list(extra))[:10]}"

        return True, "ok"

    # =========================================================
    # Thread helpers: split/number/hashtags-last-only
    # =========================================================
    def _normalize_thread_parts(self, raw: str):
        parts = [p.strip() for p in raw.split(THREAD_DELIM) if p.strip()]
        if not parts:
            parts = [raw.strip()]
        return parts

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
        tags = self._enforce_hashtag_policy(self.DEFAULT_HASHTAGS)[: self.MAX_HASHTAGS]
        tag_line = " ".join(tags).strip()

        last = tweets[-1].rstrip()
        # keep hashtags as last line
        last = f"{last}\n\n{tag_line}".strip()
        if self.SIGNATURE:
            last = (last + f" {self.SIGNATURE}").strip()

        # trim while keeping tags
        if len(last) > TWEET_LIMIT:
            reserve = len("\n\n" + tag_line) + (len(" " + self.SIGNATURE) if self.SIGNATURE else 0)
            body_max = max(0, TWEET_LIMIT - reserve)
            body = tweets[-1]
            body = body[:max(0, body_max - 1)].rstrip() + "…" if body_max > 0 else ""
            last = f"{body}\n\n{tag_line}".strip()
            if self.SIGNATURE:
                last = (last + f" {self.SIGNATURE}").strip()

        tweets[-1] = last
        return tweets

    # =========================================================
    # Posting
    # =========================================================
    def _publish_tweet(self, text: str, in_reply_to_tweet_id=None):
        if not self._can_post_monthly(1):
            logging.info("🛑 إيقاف النشر: تجاوز حد النشر الشهري.")
            self._audit("blocked_post_cap", {"cap": POST_CAP_MONTHLY}, content_type="guard")
            return None

        if not self._can_post_15m(1):
            logging.info("🛑 إيقاف النشر: قربت تتجاوز حد 15 دقيقة (soft).")
            self._audit("blocked_post_15m", {"soft": POSTS_PER_15MIN_SOFT}, content_type="guard")
            return None

        if self.DRY_RUN:
            logging.info(f"[DRY_RUN] Tweet:\n{text}\n")
            self._mark_posted_monthly(1)
            self._mark_post_15m(1)
            return f"dry_{random.randint(1000,9999)}"

        if in_reply_to_tweet_id:
            resp = self.client_v2.create_tweet(text=text, in_reply_to_tweet_id=in_reply_to_tweet_id, user_auth=True)
        else:
            resp = self.client_v2.create_tweet(text=text, user_auth=True)

        tid = resp.data["id"]
        self._mark_posted_monthly(1)
        self._mark_post_15m(1)
        return tid

    def _publish_thread(self, tweets, pillar=None):
        needed = len(tweets)
        if not self._can_post_monthly(needed):
            logging.info("🛑 إيقاف الثريد: سيؤدي لتجاوز حد النشر الشهري.")
            self._audit("blocked_thread_post_cap", {"needed": needed, "cap": POST_CAP_MONTHLY}, content_type="guard")
            return []

        if not self._can_post_15m(needed):
            logging.info("🛑 إيقاف الثريد: عدد التغريدات قد يضغط حد 15 دقيقة.")
            self._audit("blocked_thread_15m", {"needed": needed, "soft": POSTS_PER_15MIN_SOFT}, content_type="guard")
            return []

        prev_id = None
        ids = []

        for idx, t in enumerate(tweets):
            if idx > 0:
                self._sleep_jitter(1.1, 1.5)

            tid = self._publish_tweet(t, in_reply_to_tweet_id=prev_id)
            if not tid:
                break
            prev_id = tid
            ids.append(tid)

        if ids:
            self._audit("thread_posted", {"pillar": pillar, "tweet_ids": ids}, content_type="thread")

        return ids

    # =========================================================
    # Poll adaptive learning
    # =========================================================
    def _init_perf_bucket(self, pillar):
        self.state.setdefault("poll_perf", {})
        self.state["poll_perf"].setdefault(pillar, {})
        for lvl in LEVELS:
            self.state["poll_perf"][pillar].setdefault(lvl, {"polls": 0, "eng_sum": 0, "reply_sum": 0})
        self._save_state()

    def _classify_level_from_text(self, text: str) -> str:
        t = (text or "").lower()

        beginner_kw = [
            "مبتدئ", "أنا جديد", "جديد", "وش يعني", "ما معنى", "شرح بسيط", "ببساطة", "من وين أبدأ", "أساسيات",
            "what is", "beginner", "basics", "eli5", "how to start"
        ]
        advanced_kw = [
            "rag", "vector", "embedding", "orchestration", "agentic", "sre", "slo", "error budget",
            "latency", "profil", "kubernetes", "terraform", "observability", "distributed", "scalability"
        ]
        intermediate_kw = [
            "best practice", "مشكلة", "حل", "تكلفة", "debug", "testing", "unit test", "refactor", "clean code",
            "cost", "billing", "security", "iam", "performance"
        ]

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

        best = max(score, key=lambda x: score[x])
        return best if score[best] > 0 else "intermediate"

    def _poll_has_ended(self) -> bool:
        last = self.state.get("last_poll_at")
        if not last:
            return False
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            return False
        delta = datetime.now(timezone.utc) - last_dt
        return delta.total_seconds() >= (POLL_DURATION_MINUTES * 60)

    def _infer_level_from_poll_replies(self, poll_id: str) -> str:
        # Guard read
        if not self._can_read_monthly(1):
            return "intermediate"

        try:
            query = f"conversation_id:{poll_id} -is:retweet"
            res = self.client_v2.search_recent_tweets(query=query, max_results=50, user_auth=True)
            self._mark_read_monthly(1)

            if not res or not res.data:
                return "intermediate"

            votes = {"beginner": 0, "intermediate": 0, "advanced": 0}
            for tw in res.data:
                lvl = self._classify_level_from_text(getattr(tw, "text", ""))
                votes[lvl] += 1

            best = max(votes, key=lambda k: votes[k])
            return best if votes[best] > 0 else "intermediate"

        except Exception:
            return "intermediate"

    def _get_poll_engagement_score(self, poll_id: str) -> int:
        # Guard read
        if not self._can_read_monthly(1):
            return 0
        try:
            tw = self.client_v2.get_tweet(
                id=poll_id,
                tweet_fields=["public_metrics"],
                user_auth=True
            )
            self._mark_read_monthly(1)

            if not tw or not tw.data or not getattr(tw.data, "public_metrics", None):
                return 0

            m = tw.data.public_metrics
            likes = int(m.get("like_count", 0))
            replies = int(m.get("reply_count", 0))
            rts = int(m.get("retweet_count", 0))
            quotes = int(m.get("quote_count", 0))

            # weighted score
            score = replies * 3 + quotes * 3 + rts * 2 + likes
            return score

        except Exception:
            return 0

    def _update_poll_learning(self):
        if not self._poll_has_ended():
            return
        if self.state.get("last_poll_processed") is True:
            return

        poll_id = self.state.get("last_poll_id")
        pillar = self.state.get("last_poll_pillar")
        used_level = self.state.get("last_poll_level")

        if not poll_id or not pillar or not used_level:
            return

        self._init_perf_bucket(pillar)

        inferred_level = self._infer_level_from_poll_replies(poll_id)
        score = self._get_poll_engagement_score(poll_id)

        self.state["poll_perf"][pillar][used_level]["polls"] += 1
        self.state["poll_perf"][pillar][used_level]["eng_sum"] += score
        self.state["poll_perf"][pillar][inferred_level]["reply_sum"] += 1

        self.state["last_poll_processed"] = True
        self._save_state()

        self._audit("poll_learned", {
            "pillar": pillar,
            "level": used_level,
            "inferred_level": inferred_level,
            "score": score
        }, content_type="poll")

    def _choose_level_for_pillar(self, pillar: str) -> str:
        """
        70% choose best avg engagement; 20% choose reply-pref; 10% random exploration
        """
        self._init_perf_bucket(pillar)
        perf = self.state["poll_perf"][pillar]

        avgs = {}
        for lvl in LEVELS:
            polls = max(1, int(perf[lvl].get("polls", 0)))
            avgs[lvl] = perf[lvl].get("eng_sum", 0) / polls

        best_level = max(avgs, key=lambda k: avgs[k])
        reply_pref = max(perf, key=lambda k: perf[k].get("reply_sum", 0))

        r = random.random()
        if r < 0.70:
            return best_level
        elif r < 0.90:
            return reply_pref
        else:
            return random.choice(LEVELS)

    # =========================================================
    # Poll mode
    # =========================================================
    def _should_run_poll(self):
        if not POLL_MODE:
            return False
        last = self.state.get("last_poll_at")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            return True
        delta = datetime.now(timezone.utc) - last_dt
        return delta.days >= POLL_EVERY_DAYS

    def _pick_poll_pillar(self):
        pillars = [p for p in POLL_CONFIG.keys() if p in self.content_pillars]
        if not pillars:
            return None
        idx = int(self.state.get("poll_pillar_index", 0)) % len(pillars)
        pillar = pillars[idx]
        self.state["poll_pillar_index"] = (idx + 1) % len(pillars)
        self._save_state()
        return pillar

    def _post_poll(self):
        if not self._automation_compliance_guard("poll"):
            return

        pillar = self._pick_poll_pillar()
        if not pillar:
            return

        # adaptive level selection
        level = self._choose_level_for_pillar(pillar)
        cfg = POLL_CONFIG[pillar]["levels"].get(level, POLL_CONFIG[pillar]["levels"]["intermediate"])

        question = POLL_CONFIG[pillar]["question"]
        options = cfg["options"][:4]

        if not self._can_post_monthly(1) or not self._can_post_15m(1):
            logging.info("🛑 منع Poll بسبب حدود النشر.")
            return

        if self.DRY_RUN:
            logging.info(f"[DRY_RUN] Poll ({pillar}/{level}): {question} | {options}")
            poll_id = f"dry_poll_{random.randint(1000,9999)}"
        else:
            resp = self.client_v2.create_tweet(
                text=question,
                poll_options=options,
                poll_duration_minutes=POLL_DURATION_MINUTES,
                user_auth=True
            )
            poll_id = resp.data["id"]
            self._mark_posted_monthly(1)
            self._mark_post_15m(1)

        self.state["last_poll_at"] = datetime.now(timezone.utc).isoformat()
        self.state["last_poll_id"] = poll_id
        self.state["last_poll_pillar"] = pillar
        self.state["last_poll_level"] = level
        self.state["last_poll_processed"] = False
        self._save_state()

        self._audit("poll_posted", {"pillar": pillar, "level": level, "poll_id": poll_id}, content_type="poll")
        logging.info(f"📊 Poll posted ({pillar}/{level}): {poll_id}")

    # =========================================================
    # Determine keyword focus from last poll option (simple heuristic)
    # (We don't fetch actual poll result; we use inferred level + use pillar as direction)
    # =========================================================
    def _get_keyword_for_pillar_from_level(self, pillar: str, level: str):
        """
        Choose a keyword set seed for filtering RSS.
        We use the first option's keyword list as a loose filter seed (safe).
        """
        try:
            cfg = POLL_CONFIG[pillar]["levels"][level]
            # pick the first option and its keywords, use first keyword as filter seed
            opt = cfg["options"][0]
            kws = cfg.get("keywords", {}).get(opt, [])
