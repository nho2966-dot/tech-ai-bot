import os
import csv
import logging
from datetime import datetime
import requests
import random

# === Logging setup ===
logging.basicConfig(level=logging.INFO, format="🛡️ %(asctime)s - %(message)s")

# === قراءة مفاتيح البيئة ===
CONFIG_YAML = os.getenv("CONFIG_YAML")
GEMINI_KEY = os.getenv("GEMINI_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_KEY")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOKEN = os.getenv("TG_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# === إعداد المحركات البديلة ===
ENGINES = {
    "gemini": GEMINI_KEY,
    "google": GOOGLE_API_KEY,
    "openai": OPENAI_API_KEY,
    "openrouter": OPENROUTER_API_KEY,
    "qwen": QWEN_API_KEY,
    "xai": XAI_API_KEY,
    "tavily": TAVILY_KEY,
}

# === وظيفة اختيار المحرك المتاح ===
def choose_engine(preferred=None):
    if preferred and ENGINES.get(preferred):
        return preferred, ENGINES[preferred]
    # اختيار أي محرك متاح بشكل عشوائي
    available = {k: v for k, v in ENGINES.items() if v}
    if not available:
        logging.error("لا يوجد أي محرك مفعل! تحقق من مفاتيح البيئة.")
        return None, None
    engine = random.choice(list(available.keys()))
    return engine, available[engine]

# === وظيفة تسجيل الأحداث في CSV ===
def log_event(prompt, response, engine):
    filename = "bot_log.csv"
    fieldnames = ["datetime", "engine", "prompt", "response"]
    exists = os.path.isfile(filename)
    with open(filename, mode='a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({
            "datetime": datetime.now().isoformat(),
            "engine": engine,
            "prompt": prompt,
            "response": response
        })

# === وظيفة إرسال التنبيهات إلى Telegram ===
def send_telegram(message):
    if not TG_CHAT_ID or not TG_TOKEN:
        logging.warning("مفاتيح Telegram غير مفعلة.")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            logging.info("تم إرسال التنبيه إلى Telegram بنجاح.")
        else:
            logging.error(f"خطأ في إرسال Telegram: {r.text}")
    except Exception as e:
        logging.error(f"استثناء عند إرسال Telegram: {e}")

# === مثال على وظيفة الرد على المستخدم ===
def get_response(prompt, preferred_engine=None):
    engine, key = choose_engine(preferred_engine)
    if not engine:
        return "لا يوجد محرك متاح حاليًا."
    
    # هنا ضع منطق الطلب لكل محرك (API call) حسب مفتاحه
    # للمثال سنقوم برد تجريبي
    response = f"[{engine.upper()} رد تجريبي] على: {prompt}"
    
    log_event(prompt, response, engine)
    send_telegram(f"محرك: {engine} | استجابة على: {prompt}")
    
    return response

# === مثال على التشغيل ===
if __name__ == "__main__":
    while True:
        user_input = input("أدخل السؤال: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break
        reply = get_response(user_input)
        print(f"🤖 الرد: {reply}")
