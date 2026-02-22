import os
import sqlite3
import random
import time
from datetime import datetime
from google import genai 
import requests

# -------------------- إعدادات أيبكس --------------------
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

APEX_RULES = """
- الهوية: أيبكس، خبير تقني خليجي مطلع.
- التخصص: Artificial Intelligence and its latest tools والأجهزة الذكية للأفراد.
- المهمة: كشف "الأسرار والخبايا" (Tech Secrets) للأفراد.
- اللهجة: خليجية بيضاء.
- الممنوعات: لا تذكر 'Industrial Revolution'، لا صيني، لا أكواد.
"""

# -------------------- تهيئة المحرك --------------------
client = genai.Client(api_key=GEMINI_KEY)

def init_db():
    if not os.path.exists('data'): os.makedirs('data')
    conn = sqlite3.connect('data/apex_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (content TEXT, type TEXT, date TEXT)''')
    conn.commit()
    return conn

def generate_apex_content():
    scenarios = [
        "سر مخفي في أداة ذكاء اصطناعي يفيد الأفراد",
        "ميزة رهيبة في الأيفون أو الأندرويد تخص الذكاء الاصطناعي",
        "تطبيق AI جديد يسهل حياة الناس اليومية"
    ]
    topic = random.choice(scenarios)
    prompt = f"{topic}. الشروط: {APEX_RULES}"
    
    try:
        # التعديل النهائي لاسم الموديل ليكون متوافق مع API v1
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ خطأ التوليد: {e}")
        return None

def send_telegram(message):
    if not TG_TOKEN or not TG_CHAT_ID: return
    # تنظيف الـ ID من أي مسافات مخفية
    clean_id = str(TG_CHAT_ID).strip()
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": clean_id, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        print(f"📡 رد تليجرام: {res.text}")
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

def main():
    conn = init_db()
    content = generate_apex_content()
    if content:
        conn.execute("INSERT INTO history VALUES (?, ?, ?)", (content, "Secret", datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        send_telegram(f"<b>🌟 سر تقني من أيبكس</b>\n\n{content}")
    else:
        print("⚠️ فشل التوليد")
        exit(1)
    conn.close()

if __name__ == "__main__":
    main()
