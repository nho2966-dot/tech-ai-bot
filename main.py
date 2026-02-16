import os
import time
import random
import logging
import sqlite3
import feedparser
import tweepy
from datetime import datetime, timedelta
from google import genai
from openai import OpenAI as OpenAIClient

# إعداد اللوج الرقمي الاحترافي
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(levelname)s] | %(message)s")
logger = logging.getLogger("Sovereign_V2")

# --- 1. طبقة الذاكرة والتحليل الذكي ---
class SovereignIntelDB:
    def __init__(self):
        self.conn = sqlite3.connect('sovereign_v2.db', check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                (id INTEGER PRIMARY KEY, provider TEXT, task TEXT, status TEXT, 
                latency REAL, timestamp DATETIME)''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS provider_health 
                (provider TEXT PRIMARY KEY, strike_count INTEGER DEFAULT 0)''')

    def log_result(self, provider, task, status, latency):
        with self.conn:
            self.conn.execute("INSERT INTO logs (provider, task, status, latency, timestamp) VALUES (?,?,?,?,?)",
                              (provider, task, status, latency, datetime.now()))
            if status == "FAIL":
                self.conn.execute('''INSERT INTO provider_health (provider, strike_count) VALUES (?, 1)
                    ON CONFLICT(provider) DO UPDATE SET strike_count = strike_count + 1''', (provider,))
            else:
                self.conn.execute("UPDATE provider_health SET strike_count = 0 WHERE provider = ?", (provider,))

    def get_dynamic_rankings(self):
        query = '''
            SELECT provider FROM logs 
            WHERE timestamp > ? 
            GROUP BY provider 
            ORDER BY COUNT(CASE WHEN status='SUCCESS' THEN 1 END) DESC, AVG(latency) ASC
        '''
        cursor = self.conn.execute(query, (datetime.now() - timedelta(hours=12),))
        return [row[0] for row in cursor.fetchall()]

# --- 2. المحرك السيادي الفائق ---
class SuperSovereignEngine:
    def __init__(self):
        self.db = SovereignIntelDB()
        self.providers_config = {
            "gemini": {"model": "gemini-2.0-flash", "type": "google"},
            "groq": {"model": "llama-3.3-70b-versatile", "type": "openai_compat", "url": "https://api.groq.com/openai/v1"},
            "openai": {"model": "gpt-4o-mini", "type": "openai_compat", "url": None},
            "qwen": {"model": "qwen-plus", "type": "openai_compat", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1"}
        }

    def _generate_prompt(self, task, audience):
        base = "أنت مستشار سيادي في Artificial Intelligence and its latest tools."
        tone = "بأسلوب خليجي وقور للأفراد" if audience == "general" else "بأسلوب تقني معمق للمتخصصين"
        focus = {
            "news": "حلل الخبر بتركيز على الأثر الشخصي.",
            "alert": "صغ تحذيراً أمنياً حازماً وخطوات عملية.",
            "contest": "صغ سؤالاً تفاعلياً للمتابعين."
        }
        return f"{base} {tone}. {focus.get(task, 'حلل الخبر.')} التزم بالاختصار (تغريدة واحدة)."

    def generate_content(self, prompt, task="news", audience="general"):
        sys_msg = self._generate_prompt(task, audience)
        history_ranked = self.db.get_dynamic_rankings()
        execution_order = history_ranked + [p for p in self.providers_config.keys() if p not in history_ranked]
        
        tried = set()
        for attempt in range(2):
            for p_name in execution_order:
                if p_name in tried: continue
                start_time = time.time()
                try:
                    logger.info(f"🛡️ محاولة عبر [{p_name}] | المهمة: {task}")
                    content = self._dispatch_call(p_name, prompt, sys_msg)
                    if content:
                        latency = time.time() - start_time
                        self.db.log_result(p_name, task, "SUCCESS", latency)
                        return content
                except Exception as e:
                    self.db.log_result(p_name, task, "FAIL", time.time() - start_time)
                    logger.warning(f"⚠️ تعثر {p_name}: {str(e)[:50]}")
                    tried.add(p_name)
            
            if attempt == 0: time.sleep(5)
        return None

    def _dispatch_call(self, name, prompt, sys_msg):
        cfg = self.providers_config[name]
        # مطابقة دقيقة لمسميات Secrets الخاصة بك
        key_map = {
            "gemini": "X_GEMINI_KEY",
            "groq": "X_GROQ_API_KEY",
            "openai": "X_OPENAI_API_KEY",
            "qwen": "X_QWEN_API_KEY"
        }
        api_key = os.getenv(key_map.get(name))
        
        if not api_key: raise ValueError(f"Missing key: {key_map.get(name)}")

        if cfg["type"] == "google":
            client = genai.Client(api_key=api_key)
            return client.models.generate_content(model=cfg["model"], contents=prompt, config={'system_instruction': sys_msg}).text.strip()
        else:
            client = OpenAIClient(api_key=api_key, base_url=cfg.get("url"))
            resp = client.chat.completions.create(
                model=cfg["model"],
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content.strip()

# --- 3. نظام النشر على X ---
class XPublisher:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

    def publish(self, text):
        try:
            # إضافة رمز زمنية مخفية لمنع رفض التغريدات المكررة
            unique_text = f"{text}\n\u200c" 
            response = self.client.create_tweet(text=unique_text)
            logger.info(f"✅ تم النشر بنجاح! ID: {response.data['id']}")
            return True
        except Exception as e:
            logger.error(f"❌ فشل النشر على X: {e}")
            return False

# --- 4. العقل المدبر (Orchestrator) ---
def main():
    # جلب خبر (مثال من RSS)
    feed = feedparser.parse("https://hnrss.org/newest?q=AI")
    if not feed.entries: return
    
    top_story = feed.entries[0]
    prompt = f"الخبر: {top_story.title}. التفاصيل: {top_story.summary}"
    
    engine = SuperSovereignEngine()
    publisher = XPublisher()
    
    content = engine.generate_content(prompt, task="news", audience="general")
    
    if content:
        publisher.publish(content)
    else:
        logger.critical("🚨 تعذر توليد محتوى من جميع المزودين!")

if __name__ == "__main__":
    main()
