import os, sqlite3, logging, hashlib, re, time
from datetime import datetime
from urllib.parse import urlparse
import tweepy
from dotenv import load_dotenv
from openai import OpenAI

# 1. الحوكمة والإعدادات العليا
load_dotenv()
DB_FILE = "tech_om_sovereign_2026.db"
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

TRUSTED_SOURCES = ["techcrunch.com", "openai.com", "wired.com", "theverge.com", "bloomberg.com", "mit.edu"]

EDITORIAL_POLICY = {
    "BREAKING": {"min_score": 4, "max_len": 240, "prefix": "🚨 عاجل تقني"},
    "ANALYSIS": {"min_score": 5, "max_len": 25000, "prefix": "🧠 تحليل معمق"},
    "HARVEST":  {"min_score": 5, "max_len": 25000, "prefix": "🗞️ حصاد الأسبوع"}
}

# 2. محرك الثريدات النخبوي (إصلاح الـ Prompt Bug)
class EliteThreadEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def post_thread(self, raw_content, source_url):
        system_prompt = (
            "أنت خبير تقني خليجي نخبوي. حوّل النص التالي إلى ثريد (Thread) متماسك.\n"
            "الهيكل: (Hook جذاب -> Analysis عميق -> Takeaway عملي).\n"
            "استخدم لهجة خليجية بيضاء، وافصل بين التغريدات بعلامة '---'.\n"
            "لا تقتطع الكلمات، واجعل كل تغريدة أقل من 240 حرفاً."
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": system_prompt}, # تم الإصلاح هنا ✅
                    {"role": "user", "content": raw_content}
                ], 
                temperature=0.5
            )
            raw_tweets = r.choices[0].message.content.split("---")
            tweets = [t.strip() for t in raw_tweets if len(t.strip()) > 30]

            prev_id = None
            for i, txt in enumerate(tweets):
                header = "🧵 تحليل سيادي\n" if i == 0 else f"↳ {i+1}/{len(tweets)}\n"
                footer = f"\n\n🔗 المرجع: {source_url}" if i == len(tweets)-1 else ""
                
                final_txt = f"{header}{txt}{footer}"
                time.sleep(2) # حماية الخوارزمية
                res = self.x.create_tweet(text=final_txt, in_reply_to_tweet_id=prev_id)
                prev_id = res.data['id']
            return True
        except Exception as e:
            logging.error(f"❌ فشل الثريد: {e}")
            return False

# 3. محرك الردود الذكي (إضافة Tone Guard)
class SmartReplyEngine:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client

    def handle_mentions(self):
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me)
            if not mentions.data: return

            with sqlite3.connect(DB_FILE) as conn:
                for tweet in mentions.data:
                    rh = hashlib.sha256(f"reply_{tweet.id}".encode()).hexdigest()
                    if conn.execute("SELECT 1 FROM vault WHERE h=?", (rh,)).fetchone(): continue

                    # --- Tone Guard Logic ---
                    tone = "تحليلي وهادئ"
                    if any(word in tweet.text.lower() for word in ["ليش", "كيف", "وش", "طريقة"]):
                        tone = "تعليمي وداعم"
                    elif any(word in tweet.text for word in ["غلط", "ما أتفق", "سيء"]):
                        tone = "دبلوماسي عقلاني يمتص الغضب"

                    prompt = f"رد كخبير تقني خليجي بنبرة {tone} على: '{tweet.text}'. اذكر مصطلحاً إنجليزيًا واحدًا."
                    res = self.ai.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    self.x.create_tweet(text=res.choices[0].message.content.strip(), in_reply_to_tweet_id=tweet.id)
                    conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (rh, "REPLY", datetime.now().isoformat()))
                    logging.info(f"✅ رد ذكي بنبرة {tone} على: {tweet.id}")
        except Exception as e: logging.error(f"❌ خطأ الردود: {e}")

# 4. المحرك السيادي (Governance & Orchestration)
class SovereignEngine:
    def __init__(self):
        self._init_db()
        self._init_clients()
        self.threader = EliteThreadEngine(self.x, self.ai)
        self.replier = SmartReplyEngine(self.x, self.ai)

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS vault (h TEXT PRIMARY KEY, type TEXT, dt TEXT)")

    def _init_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def _is_trusted(self, url): # تفعيل الـ Trust Guard ✅
        domain = urlparse(url if "://" in url else f"https://{url}").netloc.replace("www.", "")
        return any(t in domain for t in TRUSTED_SOURCES)

    def publish_logic(self, raw_data, url, mode="ANALYSIS"):
        # 1. Trust Guard
        if not self._is_trusted(url):
            logging.warning(f"🛑 مصدر غير موثوق ({url}) - تم حجب النشر.")
            return

        # 2. Hash Vault (منع التكرار) ✅
        h = hashlib.sha256(raw_data.encode()).hexdigest()
        with sqlite3.connect(DB_FILE) as conn:
            if conn.execute("SELECT 1 FROM vault WHERE h=?", (h,)).fetchone():
                logging.info("🔁 محتوى مكرر - تم الإلغاء.")
                return

        # 3. AI Scoring & Formatting
        # (بقية المنطق الذي يقرر النشر كتغريدة أو ثريد بناءً على السكور)
        # عند النجاح:
        # self.threader.post_thread(enhanced_text, url)
        # conn.execute("INSERT INTO vault VALUES (?, ?, ?)", (h, mode, datetime.now().isoformat()))

if __name__ == "__main__":
    bot = SovereignEngine()
    bot.replier.handle_mentions()
    # تجربة نشر حصاد موثوق
    bot.publish_logic("أحدث ق
