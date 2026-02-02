import tweepy
import os, json, time, hashlib
import feedparser
from google import genai
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict

# ================= CONFIG =================

SOURCES = {
    "https://www.theverge.com/rss/index.xml": 0.9,
    "https://techcrunch.com/feed/": 0.9,
    "https://9to5mac.com/feed/": 0.85
}

TECH_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "chip", "gpu", 
    "processor", "llm", "openai", "google", "apple", "microsoft", 
    "meta", "smartphone", "iphone", "android", "laptop", "cybersecurity"
]

NON_TECH = ["politics", "celebrity", "music", "movie", "crime", "war"]
BREAKING_THRESHOLD = 2    
PUBLISH_LIMIT = 2         
STATE_FILE = "state.json"

# ================= BOT =================

class TechNewsroomBot:

    def __init__(self):
        # استخدام المفاتيح كما هي في الـ Secrets الخاصة بك
        self.ai = genai.Client(api_key=os.getenv("GEMINI_KEY"))

        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        self.state = self.load_state()

    # ---------- STATE ----------
    def load_state(self):
        base = {
            "published_hashes": [],
            "events": {},
            "replied": [],
            "blacklist": []
        }
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    base.update(json.load(f))
            except: pass
        return base

    def save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ---------- FILTERS ----------
    def is_technical(self, text):
        t = text.lower()
        if any(n in t for n in NON_TECH): return False
        return any(k in t for k in TECH_KEYWORDS)

    # ---------- FACT EXTRACTION ----------
    def extract_facts(self, title, summary):
        prompt = f"استخرج فقط الحقائق التقنية الأساسية (الجهة، الحدث، المجال) باختصار شديد جداً من: {title} {summary}"
        try:
            res = self.ai.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        except: return title

    def event_fingerprint(self, facts):
        return hashlib.sha256(facts.encode()).hexdigest()

    def decide_type(self, fingerprint):
        count = self.state["events"].get(fingerprint, 0)
        return "BREAKING 🚨" if count >= BREAKING_THRESHOLD else "UPDATE 💡"

    # ---------- REPLIES SYSTEM ----------
    def handle_interactions(self):
        try:
            me = self.x.get_me().data.id
            mentions = self.x.get_users_mentions(id=me).data or []
            
            for tweet in mentions:
                t_id = str(tweet.id)
                u_id = str(tweet.author_id)
                
                if t_id in self.state["replied"] or u_id == str(me) or u_id in self.state["blacklist"]:
                    continue

                # تحليل المشاعر (Sentiment Analysis)
                sentiment_prompt = f"حلل النبرة: '{tweet.text}'. إذا كانت هجومية أو بذيئة رد بكلمة 'BLOCK' فقط، وإذا كانت تقنية رد بـ 'REPLY'."
                check = self.ai.models.generate_content(model="gemini-2.0-flash", contents=sentiment_prompt).text
                
                if "BLOCK" in check:
                    self.state["blacklist"].append(u_id)
                    continue

                reply_prompt = f"بصفتك خبير تقني، رد باختصار شديد وذكاء على: {tweet.text}"
                reply_text = self.ai.models.generate_content(model="gemini-2.0-flash", contents=reply_prompt).text
                
                self.x.create_tweet(text=reply_text.strip()[:280], in_reply_to_tweet_id=tweet.id)
                self.state["replied"].append(t_id)
                self.save_state()
                time.sleep(10)
        except Exception as e: print(f"Interaction Log: {e}")

    # ---------- MAIN LOOP ----------
    def run(self):
        print(f"🚀 Tech Newsroom Online | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        raw_items = []
        for src in SOURCES:
            try:
                raw_items.extend(feedparser.parse(src).entries[:5])
            except: continue

        published = 0
        for item in raw_items:
            if published >= PUBLISH_LIMIT: break

            summary = getattr(item, "summary", "")
            combined = item.title + " " + summary

            if not self.is_technical(combined): continue

            facts = self.extract_facts(item.title, summary)
            fingerprint = self.event_fingerprint(facts)

            # تحديث عداد الحدث
            self.state["events"][fingerprint] = self.state["events"].get(fingerprint, 0) + 1
            
            if fingerprint in self.state["published_hashes"]: continue

            # قرار التحرير
            editorial_label = self.decide_type(fingerprint)
            
            # صياغة التغريدة النهائية
            publish_prompt = f"صغ تغريدة احترافية لجمهور X حول هذا الحدث: {facts}. ابدأ بـ {editorial_label} وأضف سطر 'لماذا يهمك؟'."
            final_tweet = self.ai.models.generate_content(model="gemini-2.0-flash", contents=publish_prompt).text.strip()

            try:
                self.x.create_tweet(text=final_tweet[:280])
                self.state["published_hashes"].append(fingerprint)
                published += 1
                self.save_state()
                print(f"✅ Published: {editorial_label}")
                time.sleep(30)
            except Exception as e: print(f"Publish Error: {e}")

        # معالجة الردود
        self.handle_interactions()

if __name__ == "__main__":
    bot = TechNewsroomBot()
    bot.run()
