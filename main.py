import os
import sqlite3
import random
import time
from datetime import datetime
from google import genai  # المكتبة الجديدة كما ظهرت في السجلات
import requests

# -------------------- إعدادات أيبكس (ناصر) --------------------
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# دستور أيبكس الصارم
APEX_RULES = """
- الهوية: أيبكس، خبير تقني خليجي مطلع.
- التخصص: Artificial Intelligence and its latest tools والأجهزة الذكية للأفراد.
- المهمة: كشف "الأسرار والخبايا" (Tech Secrets) والمقارنات الدقيقة التي تهم المستخدم العادي.
- اللهجة: خليجية بيضاء (عفوية ومهنية).
- الممنوعات: لا تذكر 'Industrial Revolution'، لا تستخدم الصينية، لا تضع أكواد برمجية، تجنب الهلوسة.
"""

# -------------------- تهيئة المحركات --------------------
client = genai.Client(api_key=GEMINI_KEY)

def init_db():
    if not os.path.exists('data'): os.makedirs('data')
    conn = sqlite3.connect('data/apex_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (content TEXT, type TEXT, date TEXT)''')
    conn.commit()
    return conn

# -------------------- توليد محتوى الخبايا --------------------
def generate_apex_content():
    scenarios = [
        "سر مخفي في أداة ذكاء اصطناعي (مثل برومبت سري أو ميزة غير مفعلة)",
        "خفية في أجهزة الأيفون أو الأندرويد تتعلق بالذكاء الاصطناعي",
        "مقارنة سريعة بين أداتين AI من حيث أسرار الأداء وليس المواصفات العامة",
        "طريقة مبتكرة للأفراد لاستخدام الـ AI في حياتهم اليومية (خبايا)"
    ]
    
    topic = random.choice(scenarios)
    prompt = f"اكتب تغريدة/رسالة عن: {topic}. \nالشروط: {APEX_RULES} \nابدأ بأسلوب حماسي (مثل: تدري إن.. أو خذ ه السر..)"
    
    try:
        # استخدام الطريقة الصحيحة للمكتبة الجديدة google-genai
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ خطأ في التوليد: {e}")
        return None

# -------------------- إرسال الإشعارات --------------------
def send_telegram(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠️ تنبيه: مفاتيح تليجرام ناقصة.")
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print("✅ تم الإرسال لتليجرام بنجاح.")
        else:
            print(f"❌ فشل إرسال تليجرام: {res.text}")
    except Exception as e:
        print(f"❌ خطأ اتصال تليجرام: {e}")

# -------------------- حلقة التشغيل --------------------
def main():
    print(f"🚀 تشغيل أيبكس - {datetime.now()}")
    conn = init_db()
    
    # 1. توليد المحتوى
    content = generate_apex_content()
    
    if content:
        # 2. حفظ في قاعدة البيانات
        conn.execute("INSERT INTO history VALUES (?, ?, ?)", 
                     (content, "Secret", datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        
        # 3. النشر (حالياً تليجرام، ويمكنك إضافة تويتر هنا)
        formatted_message = f"<b>🌟 سر تقني جديد من أيبكس</b>\n\n{content}"
        send_telegram(formatted_message)
        print(f"📝 المحتوى المولد:\n{content}")
    else:
        print("⚠️ لم يتم توليد محتوى.")
        exit(1) # لإخطار GitHub Actions بالفشل

    conn.close()

if __name__ == "__main__":
    main()
