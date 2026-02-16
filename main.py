import os
import time
import random
import logging
import sqlite3
from datetime import datetime, timedelta
from google import genai
from openai import OpenAI as OpenAIClient

# إعداد اللوج الرقمي الاحترافي
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(levelname)s] | %(message)s")
logger = logging.getLogger("Sovereign_V2")

class SovereignIntelDBv2:
    def __init__(self):
        self.conn = sqlite3.connect('sovereign_v2.db', check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            # سجل العمليات الكامل
            self.conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                (id INTEGER PRIMARY KEY, provider TEXT, task TEXT, status TEXT, 
                latency REAL, timestamp DATETIME)''')
            # تتبع حالة المزود (الصحة والموثوقية)
            self.conn.execute('''CREATE TABLE IF NOT EXISTS provider_health 
                (provider TEXT PRIMARY KEY, strike_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1)''')

    def log_result(self, provider, task, status, latency):
        with self.conn:
            self.conn.execute("INSERT INTO logs (provider, task, status, latency, timestamp) VALUES (?,?,?,?,?)",
                              (provider, task, status, latency, datetime.now()))
            if status == "FAIL":
                self.conn.execute("UPDATE provider_health SET strike_count = strike_count + 1 WHERE provider = ?", (provider,))
            else:
                self.conn.execute("UPDATE provider_health SET strike_count = 0, is_active = 1 WHERE provider = ?", (provider,))

    def get_dynamic_rankings(self):
        # ذكاء اصطناعي إحصائي: ترتيب المزودين بناءً على نسبة النجاح وسرعة الاستجابة في آخر 12 ساعة
        query = '''
            SELECT provider FROM logs 
            WHERE timestamp > ? 
            GROUP BY provider 
            ORDER BY COUNT(CASE WHEN status='SUCCESS' THEN 1 END) DESC, AVG(latency) ASC
        '''
        cursor = self.conn.execute(query, (datetime.now() - timedelta(hours=12),))
        ranked = [row[0] for row in cursor.fetchall()]
        return ranked



class SuperSovereignV2:
    def __init__(self):
        self.db = SovereignIntelDBv2()
        self.providers_config = {
            "gemini": {"model": "gemini-2.0-flash", "type": "google"},
            "groq": {"model": "llama-3.3-70b-versatile", "type": "openai_compat", "url": "https://api.groq.com/openai/v1"},
            "openai": {"model": "gpt-4o-mini", "type": "openai_compat", "url": None},
            "qwen": {"model": "qwen-plus", "type": "openai_compat", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1"}
        }

    def _generate_prompt_logic(self, task, audience):
        # منطق السيادة في صياغة الأوامر (System Prompt Engineering)
        base = "أنت مستشار سيادي في Artificial Intelligence and its latest tools."
        audience_tone = "بأسلوب خليجي مبسط" if audience == "general" else "بأسلوب تقني معمق"
        task_focus = {
            "news": "حلل الخبر بتركيز على الأثر الشخصي.",
            "alert": "صغ تحذيراً أمنياً حازماً وخطوات عملية.",
            "insight": "قدم رؤية استراتيجية لمستقبل الأداة.",
            "contest": "صغ سؤالاً تفاعلياً للمتابعين."
        }
        return f"{base} {audience_tone}. {task_focus.get(task, 'كن ملهماً ومختصراً.')} (تغريدة واحدة)."

    def run_sovereign_task(self, prompt, task="news", audience="general"):
        sys_msg = self._generate_prompt_logic(task, audience)
        
        # 1. جلب الترتيب الديناميكي من قاعدة البيانات (التعلم من الماضي)
        history_ranked = self.db.get_dynamic_rankings()
        all_providers = list(self.providers_config.keys())
        # دمج الترتيب التاريخي مع المزودين الذين لم يجربوا بعد
        execution_order = history_ranked + [p for p in all_providers if p not in history_ranked]
        
        tried = set()
        for attempt in range(2): # محاولتان كحد أقصى للنظام ككل
            for p_name in execution_order:
                if p_name in tried: continue
                
                start_time = time.time()
                try:
                    logger.info(f"🛡️ تنفيذ سيادي عبر [{p_name}] | المهمة: {task}")
                    content = self._dispatch_call(p_name, prompt, sys_msg)
                    
                    if content:
                        latency = time.time() - start_time
                        self.db.log_result(p_name, task, "SUCCESS", latency)
                        logger.info(f"✅ تم بنجاح عبر {p_name} ({latency:.2f}s)")
                        return content
                except Exception as e:
                    self.db.log_result(p_name, task, "FAIL", time.time() - start_time)
                    logger.warning(f"⚠️ تعثر {p_name}: {str(e)[:50]}")
                    tried.add(p_name)
            
            # Exponential Backoff في حال فشل الجميع في الدورة الأولى
            if attempt == 0:
                wait = 10
                logger.info(f"🚨 فشل جماعي للمزودين. إعادة المحاولة الشاملة بعد {wait} ثانية...")
                time.sleep(wait)

        return "⚠️ النظام السيادي في وضع الصيانة التلقائية نتيجة ضغط عالمي على المزودين."

    def _dispatch_call(self, name, prompt, sys_msg):
        cfg = self.providers_config[name]
        key = os.getenv(f"{name.upper()}_KEY") or os.getenv(f"{name.upper()}_API_KEY")
        
        if cfg["type"] == "google":
            client = genai.Client(api_key=key)
            return client.models.generate_content(model=cfg["model"], contents=prompt, config={'system_instruction': sys_msg}).text.strip()
        else:
            client = OpenAIClient(api_key=key, base_url=cfg.get("url"))
            resp = client.chat.completions.create(
                model=cfg["model"],
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content.strip()

# --- محاكاة التشغيل النهائي ---
if __name__ == "__main__":
    sov_v2 = SuperSovereignV2()
    # تجربة تحليل خبر عاجل بأسلوب احترافي
    news_prompt = "إطلاق أداة جديدة تترجم لغة الإشارة إلى صوت عبر الذكاء الاصطناعي"
    print(sov_v2.run_sovereign_task(news_prompt, task="news", audience="general"))
