import os, sqlite3, logging, hashlib, time, random, re
from datetime import datetime, timedelta
import tweepy, feedparser
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="🛡️ %(message)s")

# السياسة السيادية (الخبير التقني الخليجي المحلل)
POLICY = (
    "أنت خبير ومحلل تقني خليجي نخبوي. القواعد الصارمة:\n"
    "1. اللغة: العربية (الخليجية البيضاء) حصراً، مع مصطلحات إنجليزية بين قوسين ().\n"
    "2. الذكاء: لا تنقل الخبر فقط، بل قارنه بالمنافسين ووضح أثره المستقبلي (Impact Prediction).\n"
    "3. الهيكل: (Hook) ثم (Value + المقارنة) ثم (Impact) ثم (CTA).\n"
    "4. الجودة: منع الهلوسة، منع الأخبار القديمة، منع الرموز الغريبة.\n"
    "5. الفلتر: يُمنع الرد على النفس أو تكرار الرد لنفس الشخص في نفس السياق."
)

class EliteSovereignSystem:
    def __init__(self):
        self._setup_db()
        self._setup_clients()
        self.bot_id = self.x.get_me().data.id

    def _setup_db(self):
        with sqlite3.connect("sovereign_v58.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS v (h PRIMARY KEY, type TEXT, dt TEXT)")

    def _setup_clients(self):
        self.x = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"), consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"), access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        self.ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

    def is_clean_and_valid(self, text):
        """فلتر النقاء اللغوي ومنع الرموز الغريبة"""
        if not text: return False
        clean_pattern = re.compile(r'^[ \u0600-\u06FF\u0750-\u077F0-9a-zA-Z()\[\]\.\!\?\-\n\r]+$')
        if not clean_pattern.match(text) or re.search(r'[\?\!\.]{4,}', text):
            return False
        return True

    def _ai_call(self, user_p, high_temp=False):
        """استدعاء الذكاء الاصطناعي مع فحص الحقائق ومنع الهلوسة"""
        try:
            res = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": POLICY}, {"role": "user", "content": user_p}],
                temperature=0.7 if high_temp else 0.3 # درجة حرارة منخفضة لمنع الهلوسة
            ).choices[0].message.content.strip()
            return res if self.is_clean_and_valid(res) else ""
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return ""

    def handle_mentions(self):
        """محرك الردود الذكي بفلتر صارم"""
        mentions = self.x.get_users_mentions(id=self.bot_id, tweet_fields=['author_id', 'text'])
        if not mentions.data: return
        
        with sqlite3.connect("sovereign_v58.db") as conn:
            for t in mentions.data:
                h = hashlib.sha256(f"{t.author_id}_{t.id}".encode()).hexdigest()
                # فلتر منع الرد على النفس + منع التكرار
                if t.author_id == self.bot_id or conn.execute("SELECT 1 FROM v WHERE h=?", (h,)).fetchone():
                    continue

                reply = self._ai_call(f"حلل ورد بذكاء خليجي (مصطلحات بين قوسين): {t.text}")
                if reply:
                    time.sleep(random.randint(40, 80))
                    self.x.create_tweet(text=reply, in_reply_to_tweet_id=t.id)
                    conn.execute("INSERT INTO v VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))

    def process_news(self):
        """جلب الأخبار وتطبيق فلتر الـ 36 ساعة والقيمة المضافة"""
        feed = feedparser.parse("https://techcrunch.com/feed/")
        for entry in feed.entries[:5]:
            # فحص عمر الخبر (36 ساعة)
            p_date = datetime(*entry.published_parsed[:6])
            is_old = (datetime.now() - p_date) > timedelta(hours=36)
            
            # إذا كان الخبر قديم، نتحقق هل يحمل "قيمة حيوية" دائمة؟
            check_val = self._ai_call(f"هل هذه معلومة حيوية دائمة أم خبر مؤقت؟ أجب بـ (VITAL/NEWS): {entry.title}")
            
            if is_old and "VITAL" not in check_val:
                continue # استبعاد الأخبار القديمة التي ليست حيوية

            h = hashlib.sha256(entry.title.encode()).hexdigest()
            with sqlite3.connect("sovereign_v58.db") as conn:
                if conn.execute("SELECT 1 FROM v WHERE h=?", (h,)).fetchone(): continue
                
                # صياغة المحتوى مع وحدة الاستخبارات (المقارنة والاستشراف)
                prompt = f"حلل الخبر، قارنه بالمنافسين، وصغ ثريد خليجي (Hook-Value-Impact-CTA) فواصل '---':\n{entry.title}\n{entry.description}"
                content = self._ai_call(prompt, high_temp=True)
                
                if content:
                    tweets = [t.strip() for t in content.split("---") if len(t.strip()) > 10]
                    p_id = None
                    for i, txt in enumerate(tweets):
                        time.sleep(random.randint(120, 180))
                        msg = f"{txt}\n.\n🕒 {datetime.now().strftime('%H:%M')}" if i == 0 else txt
                        res = self.x.create_tweet(text=msg, in_reply_to_tweet_id=p_id)
                        p_id = res.data['id']
                    conn.execute("INSERT INTO v VALUES (?,?,?)", (h, "THREAD", datetime.now().isoformat()))
                    break # نشر ثريد واحد دسم في كل دورة

if __name__ == "__main__":
    bot = EliteSovereignSystem()
    bot.process_news()
    bot.handle_mentions()
