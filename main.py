import os, sqlite3, logging, hashlib, re, time
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. إعدادات البيئة والحوكمة (Governance)
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# السياسة التحريرية النخبوية
EDITORIAL_POLICY = {
    "BREAKING": {"min_score": 4, "max_len": 500, "prefix": "🚨 عاجل تقني"},
    "ANALYSIS": {"min_score": 4, "max_len": 25000, "prefix": "🧠 تحليل معمق"},
    "OPINION":  {"min_score": 5, "max_len": 25000, "prefix": "🗣️ رأي تقني"},
    "CONTEST":  {"min_score": 5, "max_len": 280, "prefix": "🏆 مسابقة الأسبوع"},
    "HARVEST":  {"min_score": 5, "max_len": 25000, "prefix": "🗞️ حصاد الأسبوع"}
}

TRUSTED_SOURCES = ["theverge.com", "techcrunch.com", "wired.com", "openai.com", "mit.edu", "reuters.com", "bloomberg.com"]

# 2. محرك الثريدات النخبوي (Elite Thread Engine)
class TechThreadUltimate:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client
        self.max_len = 250

    def _dedupe_terms(self, text):
        seen = set()
        words = text.split()
        out = []
        for w in words:
            clean_w = re.sub(r"[()]", "", w).lower()
            if clean_w.isascii() and len(clean_w) > 2:
                if clean_w in seen: continue
                seen.add(clean_w)
            out.append(w)
        return " ".join(out)

    def _sanitize_tweets(self, tweets):
        clean = []
        for t in tweets:
            t = self._dedupe_terms(t.strip())
            if len(t) < 45: continue
            if len(t) > self.max_len:
                t = t[:self.max_len - 3] + "..."
            clean.append(t)
        return clean

    def post_thread(self, raw_content, source_url):
        prompt = (
            "حوّل النص إلى ثريد خليجي نخبوي (Hook -> Analysis -> Takeaway).\n"
            "افصل بين كل تغريدة وعلامة '---'. استخدم لهجة بيضاء ومصطلحات تقنية."
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "user", "content": raw_content}], temperature=0.5
            )
            raw_res = r.choices[0].message.content.strip().split("---")
            tweets = self._sanitize_tweets(raw_res)

            if len(tweets) < 3: return None

            # Semantic Hook Guard
            if not re.search(r"(ليش|كيف|وش|هل|السبب|الفرق)", tweets[0]):
                tweets[0] = "ليش هذا الموضوع مهم الحين؟ خلّك معي في هالتحليل.. 👇\n\n" + tweets[0]
            if not re.search(r"[!?🔥🚨🧠]", tweets[0]): tweets[0] = "🧠 " + tweets[0]

            previous_tweet_id = None
            for i, tweet_text in enumerate(tweets):
                if i == len(tweets)-1:
                    if "؟" not in tweet_text: tweet_text += "\n\nوش رأيك؟ تتفق أو لا؟ 👇"
                    footer = f"\n\n🔗 المصدر: {source_url}"
                else: footer = ""

                header = "🧵 بداية التحليل\n" if i == 0 else f"↳ {i+1}/{len(tweets)}\n"
                final_text = f"{header}{tweet_text}{footer}"

                time.sleep(1.2 if i == 0 else 0.7)
                response = self.x.create_tweet(text=final_text, in_reply_to_tweet_id=previous_tweet_id)
                previous_tweet_id = response.data["id"]
                logging.info(f"✅ تم نشر جزء الثريد {i+1}")
            return previous_tweet_id
        except Exception as e:
            logging.error(f"❌ فشل الثريد: {e}")
            return None

# 3. المحرك الأساسي (Sovereign Engine)
class TechSovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.year = 2026
        self.threader = TechThreadUltimate(self.x, self.ai)

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")
            conn.commit()

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_duplicate(self, text):
        h = hashlib.sha256(text.strip().encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            return conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone() is not None, h

    def _is_trusted(self, url):
        parsed = urlparse("https://" + url if not url.startswith("http") else url)
        domain = parsed.netloc.lower()
        return any(domain == d or domain.endswith("." + d) for d in TRUSTED_SOURCES)

    def publish(self, raw_input, source_url, mode="ANALYSIS"):
        if not self._is_trusted(source_url):
            logging.warning(f"🛑 مصدر غير موثوق: {source_url}")
            return

        prompt = (f"أنت رئيس تحرير خليجي في 2026. النمط: {mode}.\n"
                  "استخدم لهجة خليجية بيضاء، ضع مصطلحين إنجليزيين بين قوسين.\n"
                  "أنهِ بـ: [SCORE: X/5]")
        
        r = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": raw_input}], temperature=0.4
        )
        enhanced = r.choices[0].message.content.strip()

        score_match = re.search(r"\[SCORE:\s*(\d)/5\]", enhanced)
        score = int(score_match.group(1)) if score_match else 0
        clean_text = re.sub(r"\[.*?\]", "", enhanced).strip()
        
        policy = EDITORIAL_POLICY.get(mode)
        if score < policy["min_score"]: return

        is_dup, h = self._is_duplicate(clean_text)
        if is_dup: return

        # قرار النشر: ثريد للتحليل والحصاد، أو تغريدة واحدة للبقية
        if mode in ["ANALYSIS", "HARVEST"] and score == 5:
            self.threader.post_thread(clean_text, source_url)
        else:
            full_post = f"{policy['prefix']} {self.year}\n\n{clean_text[:policy['max_len']]}\n\n🔗 المرجع: {source_url}"
            self.x.create_tweet(text=full_post)
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, mode, datetime.now().isoformat()))
        logging.info(f"🚀 تم تنفيذ {mode} بنجاح!")

    def auto_run(self):
        day = datetime.now().strftime("%A")
        if day == "Friday":
            self.publish("حصاد تقني دسم لأهم 3 ابتكارات في AI هذا الأسبوع.", "techcrunch.com", "HARVEST")
        elif day == "Monday":
            self.publish("سؤال مسابقة تقنية عن الثورة الصناعية الرابعة.", "mit.edu", "CONTEST")
        else:
            self.publish("نصيحة تقنية يومية عن الإنتاجية باستخدام الأدوات الذكية.", "openai.com", "BREAKING")

if __name__ == "__main__":
    engine = TechSovereignEngine()
    # تشغيل الاختبار المباشر (حصاد الأسبوع)
    test_content = "أهم أحداث الأسبوع: Sora 2.0 يذهل العالم، ومعالجات الكم الجديدة من NVIDIA تصل للمستهلكين."
    engine.publish(test_content, "techcrunch.com", mode="HARVEST")
