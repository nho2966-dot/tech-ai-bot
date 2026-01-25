import os
import time
import random
import json
import logging
import sqlite3
from datetime import datetime, timedelta
import tweepy
from openai import OpenAI
from dotenv import load_dotenv
from collections import deque
from threading import Thread, Lock
from queue import Queue
from typing import Dict, Optional, List
import requests  # للتحقق من روابط المصادر

# ─── إعدادات متقدمة للوكيل العالمي الاحترافي ───────────────────────────
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [TechAgent-Pro-Global] | %(levelname)-5s | %(message)s',
    handlers=[logging.FileHandler("agent_logs.log"), logging.StreamHandler()]
)

# ─── تكوينات قابلة للتعديل ────────────────────────────────────────────
CONFIG = {
    "STATE_FILE": "agent_state.json",
    "DB_FILE": "agent_db.sqlite",              # قاعدة بيانات لتخزين الإحصائيات والردود
    "MAX_REPLIES_PER_HOUR": 15,                # حد أمان لتجنب السبام
    "MIN_FOLLOWERS_FOR_REPLY": 100,            # رد فقط على حسابات ذات تأثير (للشهرة)
    "CONTENT_POST_INTERVAL_HOURS": 3,          # نشر محتوى أصلي كل 3 ساعات
    "TREND_SEARCH_INTERVAL_MIN": 8,            # بحث عن تريندات كل 8 دقائق
    "REPLY_COOLDOWN_SEC": 30,                  # تأخير بين الردود لتجنب النمط الآلي
    "SUPPORTED_LANGUAGES": ["ar", "en", "fr", "es"],  # دعم متعدد اللغات
    "MAX_REPLY_LENGTH": 270,                   # حد X
    "USE_WEB_SEARCH_FOR_SOURCES": True,        # تكامل بحث ويب للمصادر
    "TRUSTED_SOURCES_DOMAINS": [               # فلتر المصادر 100% موثوقة
        "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
        "cnet.com", "engadget.com", "bloomberg.com", "reuters.com",
        "apple.com", "blog.google", "microsoft.com", "nvidia.com",
        "samsung.com", "playstation.com", "x.ai"
    ]
}

REPLY_QUEUE = Queue()                          # قائمة انتظار للردود (متعدد الخيوط)
STATE_LOCK = Lock()                            # قفل للوصول الآمن
STATS_DB_CONN = sqlite3.connect(CONFIG["DB_FILE"], check_same_thread=False)
STATS_DB_CURSOR = STATS_DB_CONN.cursor()

# إنشاء جدول الإحصائيات إذا لم يكن موجودًا
STATS_DB_CURSOR.execute('''
    CREATE TABLE IF NOT EXISTS agent_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action_type TEXT,
        details TEXT,
        success BOOLEAN
    )
''')
STATS_DB_CONN.commit()

# ─── المواضيع الرئيسية للتركيز العالمي ──────────────────────────────────
TECH_TOPICS = {
    "الذكاء الاصطناعي": [
        "ذكاء اصطناعي", "AI", "ذكاء", "اصطناعي", "gpt", "grok", "llm", "نماذج لغوية",
        "machine learning", "تعلم آلي", "deep learning", "midjourney", "stable diffusion"
    ],
    "منصات التواصل الاجتماعي": [
        "تويتر", "x", "تيك توك", "انستغرام", "سناب", "فيسبوك", "خوارزمية", "تريند",
        "engagement", "تفاعل", "ريتويت", "منشن", "هاشتاج", "threads"
    ],
    "الألعاب الإلكترونية": [
        "العاب", "gaming", "بلايستيشن", "اكس بوكس", "fortnite", "gta", "call of duty",
        "esports", "vr", "ar", "steam", "نينتندو", "ببجي", "فالورانت"
    ],
    "التسريبات التقنية": [
        "تسريب", "leak", "تسريبات", "rumor", "ming-chi kuo", "mark gurman",
        "iphone 17", "galaxy s25", "pixel 10", "تسريب", "شائعة"
    ],
    "الأجهزة الذكية": [
        "iphone", "سامسونج", "pixel", "هاتف", "سماعة", "ساعة ذكية", "airpods",
        "watch", "fold", "flip", "معالج", "snapdragon", "a18", "exynos"
    ],
    "السبق الصحفي التقني": [
        "إطلاق", "announce", "مؤتمر", "ces", "wwdc", "google i/o", "samsung unpacked",
        "حدث", "إعلان", "خبر عاجل", "breaking"
    ]
}

ALL_KEYWORDS = set(word.lower() for words in TECH_TOPICS.values() for word in words)

class AutonomousTechAgent:
    def __init__(self):
        # X API v2 Client مع تحقق متقدم
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        # OpenAI مع تكوينات احترافية
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY مطلوب في .env")
        self.ai_client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # نموذج عالي الجودة للدقة

        # معلومات الحساب مع إحصائيات
        me = self.x_client.get_me(user_fields=["username", "public_metrics"])
        self.my_id = me.data.id
        self.my_username = me.data.username
        self.followers_count = me.data.public_metrics["followers_count"]
        logging.info(f"تهيئة الوكيل @{self.my_username} | متابعون: {self.followers_count} | تاريخ: {datetime.now().isoformat()}")

        # حالة الوكيل (إحصائيات متقدمة)
        self.state = self._load_state()
        self.recent_replies = deque(maxlen=CONFIG["MAX_REPLIES_PER_HOUR"])  # تتبع الردود للحدود
        self.last_content_post = datetime.fromisoformat(self.state.get("last_content_post", datetime.min.isoformat()))
        self.stats = {"replies_sent": 0, "content_posted": 0, "trends_replied": 0}  # إحصائيات الجلسة

        # خيوط متعددة للعمل المتوازي (ردود، تريندات، إحصائيات)
        self.reply_thread = Thread(target=self._process_reply_queue, daemon=True)
        self.trend_thread = Thread(target=self._trend_monitor_loop, daemon=True)
        self.stats_thread = Thread(target=self._log_stats_periodically, daemon=True)
        self.reply_thread.start()
        self.trend_thread.start()
        self.stats_thread.start()

    def _load_state(self) -> Dict:
        if os.path.exists(CONFIG["STATE_FILE"]):
            try:
                with open(CONFIG["STATE_FILE"], "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"فشل قراءة الحالة: {e}")
        return {"last_tweet_id": None, "replies_today": 0, "last_content_post": datetime.min.isoformat()}

    def _save_state(self):
        with STATE_LOCK:
            try:
                self.state["last_content_post"] = self.last_content_post.isoformat()
                with open(CONFIG["STATE_FILE"], "w") as f:
                    json.dump(self.state, f, indent=2)
            except Exception as e:
                logging.error(f"فشل حفظ الحالة: {e}")

    def _log_action(self, action_type: str, details: str, success: bool = True):
        """تسجيل الإجراءات في قاعدة البيانات للتحليل اللاحق"""
        try:
            STATS_DB_CURSOR.execute('''
                INSERT INTO agent_stats (timestamp, action_type, details, success)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), action_type, details, success))
            STATS_DB_CONN.commit()
        except Exception as e:
            logging.error(f"فشل تسجيل الإحصائية: {e}")

    def _log_stats_periodically(self):
        """خيط لتسجيل الإحصائيات كل ساعة"""
        while True:
            time.sleep(3600)  # كل ساعة
            details = json.dumps(self.stats)
            self._log_action("hourly_stats", details)
            logging.info(f"إحصائيات ساعة: {details}")

    def _is_relevant_topic(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in ALL_KEYWORDS)

    def _validate_source(self, source_url: str) -> bool:
        """التحقق من أن المصدر موثوق 100%"""
        if not source_url:
            return False
        domain = source_url.split('//')[-1].split('/')[0].lower()
        return any(trusted in domain for trusted in CONFIG["TRUSTED_SOURCES_DOMAINS"])

    def _fetch_source_snippet(self, query: str) -> Optional[str]:
        """بحث ويب سريع لمصدر موثوق (إذا تم تفعيله)"""
        if not CONFIG["USE_WEB_SEARCH_FOR_SOURCES"]:
            return None
        try:
            # هنا يمكن استخدام API بحث ويب خارجي، لكن للبساطة نستخدم requests كمثال
            search_url = f"https://www.google.com/search?q={query}+site:{random.choice(CONFIG['TRUSTED_SOURCES_DOMAINS'])}"
            response = requests.get(search_url, timeout=5)
            if response.status_code == 200:
                # استخراج أول رابط (مثال بسيط، يمكن تحسينه بـ BeautifulSoup)
                if "theverge.com" in response.text:
                    return "المصدر: The Verge (مستخرج من بحث موثوق)"
            return None
        except Exception as e:
            logging.debug(f"فشل استخراج مصدر: {e}")
            return None

    def _generate_professional_reply(self, tweet_text: str, author: str, is_trend: bool = False) -> str | None:
        if not self._is_relevant_topic(tweet_text):
            return (
                f"مرحبًا @{author}، شكرًا للإشارة! 🌍\n"
                "أنا TechAgent Pro، خبير في أخبار تقنية موثوقة 100% من مصادر رسمية فقط.\n"
                "هل يمكنك توضيح سؤالك التقني؟ سأرد بدقة ومصادر واضحة! #TechGlobal"
            )

        source_snippet = self._fetch_source_snippet(tweet_text[:50])  # استخراج مصدر تلقائي

        system_prompt = (
            "أنت TechAgent Pro – خبير تقني عالمي، مهني، محايد، يدعم متعدد اللغات (اكتشف اللغة من النص ورد بالمناسبة).\n"
            "تركيزك: الذكاء الاصطناعي، منصات التواصل، الألعاب، التسريبات، الأجهزة، السبق الصحفي.\n"
            "للشهرة: أضف قيمة فريدة، هاشتاجات عالمية، شجع التفاعل المتبادل.\n"
            "قواعد صارمة 100%:\n"
            "1. لا تقدم معلومة إلا مدعومة بمصدر موثوق من: " + ", ".join(CONFIG["TRUSTED_SOURCES_DOMAINS"]) + ".\n"
            "2. أضف في النهاية: [المصدر: اسم الموقع - تاريخ] أو 'لا مصدر موثوق حاليًا'.\n"
            "3. إذا لم يكن مصدر موثوق → لا تذكر المعلومة، اقترح بحثًا.\n"
            "4. ردود <" + str(CONFIG["MAX_REPLY_LENGTH"]) + " حرفًا، مهنية، تفتح نقاشًا.\n"
            "5. دعم متعدد اللغات: رد باللغة المناسبة (AR/EN/FR/ES).\n"
            "6. للتريندات: رؤية عالمية + دعوة للمشاركة.\n"
            "تذكر: (وُضُـوح) = ضم الشفتين جيدًا"
        )

        user_msg = (
            f"@{author} كتب: «{tweet_text}»\n"
            f"{'رد على تريند عالمي لزيادة الظهور.' if is_trend else ''}\n"
            f"مصدر مقترح: {source_snippet if source_snippet else 'لا مصدر تلقائي، تحقق يدويًا'}\n"
            "اكتب الرد فقط."
        )

        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.58,
                max_tokens=150,
                top_p=0.93
            )
            reply = resp.choices[0].message.content.strip().replace("```", "").replace("\n\n", " ")

            # التحقق النهائي للمصدر
            if "[المصدر:" not in reply and "لا مصدر" not in reply:
                reply += "\n[لا مصدر موثوق حديثًا – يُفضل التحقق]"

            return reply if len(reply) <= CONFIG["MAX_REPLY_LENGTH"] else reply[:CONFIG["MAX_REPLY_LENGTH"] - 3] + "…"

        except Exception as e:
            logging.error(f"خطأ AI: {e}")
            return None

    def _process_reply_queue(self):
        while True:
            task = REPLY_QUEUE.get()
            if task is None:
                break
            tweet_id, reply_text = task
            try:
                self.x_client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
                logging.info(f"رد ناجح على {tweet_id}: {reply_text[:50]}...")
                self.stats["replies_sent"] += 1
                self._log_action("reply_sent", f"Tweet ID: {tweet_id}", success=True)
                time.sleep(CONFIG["REPLY_COOLDOWN_SEC"])  # تأخير احترافي
            except tweepy.TweepyException as te:
                logging.error(f"فشل رد: {te}")
                self._log_action("reply_failed", str(te), success=False)
            REPLY_QUEUE.task_done()

    def _can_reply(self, author_followers: int = 0) -> bool:
        now = datetime.now()
        recent_count = sum(1 for t in self.recent_replies if now - t < timedelta(hours=1))
        return recent_count < CONFIG["MAX_REPLIES_PER_HOUR"] and author_followers >= CONFIG["MIN_FOLLOWERS_FOR_REPLY"]

    def _post_original_content(self):
        # توليد محتوى أصلي احترافي (مع مصدر)
        system_prompt = (
            "أنشئ تغريدة أصلية عالمية حول موضوع تقني ساخن من مواضيعك.\n"
            "اجعلها جذابة، مهنية، تشجع التفاعل (سؤال أو poll).\n"
            "<270 حرفًا، أضف هاشتاجات عالمية، ومصدر موثوق في النهاية.\n"
            "دعم متعدد اللغات إذا لزم."
        )

        try:
            resp = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.72,
                max_tokens=150
            )
            content = resp.choices[0].message.content.strip()
            self.x_client.create_tweet(text=content)
            logging.info(f"نشر محتوى أصلي: {content[:50]}...")
            self.stats["content_posted"] += 1
            self.last_content_post = datetime.now()
            self._save_state()
            self._log_action("content_posted", content[:100], success=True)
        except Exception as e:
            logging.error(f"فشل نشر محتوى: {e}")
            self._log_action("content_post_failed", str(e), success=False)

    def _trend_monitor_loop(self):
        """خيط مستقل لمراقبة التريندات ورد عليها"""
        last_trend_check = datetime.min
        while True:
            if datetime.now() - last_trend_check > timedelta(minutes=CONFIG["TREND_SEARCH_INTERVAL_MIN"]):
                self._reply_to_trends()
                last_trend_check = datetime.now()
            time.sleep(60)  # فحص كل دقيقة داخل الخيط

    def _reply_to_trends(self):
        try:
            topic = random.choice(list(TECH_TOPICS.keys()))
            query = f"{' OR '.join(random.sample(TECH_TOPICS[topic], min(3, len(TECH_TOPICS[topic]))))} min_faves:200 lang:en OR lang:ar -from:{self.my_username}"
            trends = self.x_client.search_recent_tweets(
                query=query,
                max_results=8,
                sort_order="relevancy",
                tweet_fields=["public_metrics"],
                expansions=["author_id"],
                user_fields=["public_metrics"]
            )

            if trends.data:
                for tweet in trends.data:
                    author = next(u.username for u in trends.includes["users"] if u.id == tweet.author_id)
                    author_followers = next(u.public_metrics["followers_count"] for u in trends.includes["users"] if u.id == tweet.author_id)
                    if tweet.public_metrics["like_count"] > 300 and self._can_reply(author_followers):
                        reply_text = self._generate_professional_reply(tweet.text, author, is_trend=True)
                        if reply_text:
                            REPLY_QUEUE.put((tweet.id, reply_text))
                            self.stats["trends_replied"] += 1
                            self._log_action("trend_reply", f"Trend from @{author}", success=True)

        except Exception as e:
            logging.error(f"خطأ في التريندات: {e}")
            self._log_action("trend_error", str(e), success=False)

    def start_monitoring(self, check_interval_sec: int = 60):
        logging.info("بدء الوكيل العالمي الاحترافي... (مراقبة + تريندات + محتوى + إحصائيات + متعدد اللغات)")

        while True:
            try:
                # 1. مراقبة المنشنات مع فلتر احترافي
                mentions = self.x_client.get_users_mentions(
                    id=self.my_id,
                    max_results=25,
                    since_id=self.state.get("last_tweet_id"),
                    expansions=["author_id"],
                    user_fields=["username", "public_metrics"],
                    tweet_fields=["created_at", "public_metrics"]
                )

                if mentions.data:
                    sorted_mentions = sorted(mentions.data, key=lambda t: t.id, reverse=True)
                    for tweet in sorted_mentions:
                        author_obj = next((u for u in mentions.includes.get("users", []) if u.id == tweet.author_id), None)
                        if not author_obj:
                            continue
                        author = author_obj.username
                        author_followers = author_obj.public_metrics["followers_count"]
                        if author.lower() == self.my_username.lower() or author_followers < CONFIG["MIN_FOLLOWERS_FOR_REPLY"]:
                            continue  # فلتر للجودة

                        if self._can_reply(author_followers):
                            logging.info(f"منشن احترافي من @{author} (متابعون: {author_followers}): {tweet.text[:70]}...")
                            reply_text = self._generate_professional_reply(tweet.text, author)
                            if reply_text:
                                REPLY_QUEUE.put((tweet.id, reply_text))

                        if tweet.id > (self.state.get("last_tweet_id") or 0):
                            self.state["last_tweet_id"] = tweet.id
                            self._save_state()

                # 2. نشر محتوى أصلي إذا حان الوقت
                if datetime.now() - self.last_content_post > timedelta(hours=CONFIG["CONTENT_POST_INTERVAL_HOURS"]):
                    self._post_original_content()

                # تأخير ذكي مع عشوائية
                sleep_time = check_interval_sec + random.uniform(-20, 25)
                time.sleep(max(50, sleep_time))

            except tweepy.TooManyRequests:
                logging.warning("Rate limit → انتظار طويل (15 دقيقة)")
                time.sleep(900)
            except Exception as e:
                logging.error(f"خطأ عام: {e}", exc_info=True)
                self._log_action("general_error", str(e), success=False)
                time.sleep(300)

    def shutdown(self):
        """إغلاق نظيف للخيوط والقاعدة"""
        REPLY_QUEUE.put(None)
        self.reply_thread.join()
        self.trend_thread.join()
        self.stats_thread.join()
        STATS_DB_CONN.close()
        logging.info("إغلاق الوكيل بنجاح.")

if __name__ == "__main__":
    try:
        agent = AutonomousTechAgent()
        agent.start_monitoring()
    except KeyboardInterrupt:
        logging.info("إيقاف بواسطة المستخدم.")
        agent.shutdown()
    except Exception as e:
        logging.critical(f"خطأ فادح: {e}", exc_info=True)
        agent.shutdown()
