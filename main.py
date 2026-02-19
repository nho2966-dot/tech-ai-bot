import os, sqlite3, random, time, threading
from datetime import datetime
import google.generativeai as genai
import openai
import tweepy
import requests
from flask import Flask, render_template_string

# -------------------- إعداد المفاتيح (بالمسميات الجديدة) --------------------
genai.configure(api_key=os.getenv("GEMINI_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")

# مسميات ناصر المعتمدة
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# دستور أيبكس (المكتسبات)
APEX_RULES = """
- اللهجة: خليجية بيضاء واضحة.
- التخصص: Artificial Intelligence and its latest tools والأجهزة الذكية للأفراد.
- التركيز: الأسرار، الخبايا، والمقارنات الجوهرية (Tech Secrets).
- الممنوعات: ذكر 'Industrial Revolution'، اللغة الصينية، الرموز البرمجية، الهلوسة التقنية.
- الشخصية: زميل تقني خبير (Peer) وليس ملقن.
"""

# -------------------- قاعدة البيانات --------------------
def init_db():
    if not os.path.exists('data'): os.makedirs('data')
    conn = sqlite3.connect('data/apex_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (content TEXT, style TEXT, type TEXT, date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stats (date TEXT PRIMARY KEY, reply_count INTEGER, posts_count INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS replies (platform TEXT, original TEXT, reply TEXT, date TEXT)''')
    conn.commit()
    return conn

# -------------------- توليد المحتوى الاحترافي --------------------
def generate_content(prompt_type):
    # تنويع البرومبت بناءً على "الأسرار والخبايا"
    prompts = {
        "secret": "اعطني سر تقني مخفي في أداة AI أو جهاز ذكي يفيد الفرد.",
        "compare": "قارن بين أداتين AI أو جهازين من حيث الخبايا الجوهرية التي لا يعرفها الكثير.",
        "bomb": "Technical Bomb: معلومة تقنية دقيقة وصادمة عن الذكاء الاصطناعي للأفراد."
    }
    
    selected_prompt = prompts.get(prompt_type, prompts["secret"])
    full_prompt = f"{selected_prompt}\n\nالقواعد الصارمة:\n{APEX_RULES}"

    try:
        # الاعتماد الأساسي على Gemini (الأكثر استقراراً حالياً)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ فشل التوليد: {e}")
        return "الذكاء الاصطناعي يغير حياتنا كل يوم، خلك مطلع! 🚀"

# -------------------- النشر والردود --------------------
def publish_telegram(content):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": content, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"⚠️ خطأ تيليجرام: {e}")

# (تم اختصار وظائف تويتر للتركيز على المنطق الحيوي)
def run_bot():
    conn = init_db()
    while True:
        try:
            print(f"\n🚀 دورة جديدة - {datetime.now()}")
            
            # 1. توليد محتوى (خبايا وأسرار)
            p_type = random.choice(["secret", "compare", "bomb"])
            content = generate_content(p_type)

            # 2. الفاصل الزمني البشري (قبل النشر)
            time.sleep(random.randint(300, 600)) 

            # 3. النشر في المنصات
            publish_telegram(content)
            # هنا تضاف وظيفة publish_twitter(content)
            
            # 4. تحديث الإحصائيات
            update_stats(conn)

            # 5. انتظار الدورة القادمة (من ساعة إلى ساعتين لضمان عدم الحظر)
            cycle_wait = random.randint(3600, 7200)
            print(f"⏳ الدورة القادمة بعد {cycle_wait//60} دقيقة...")
            time.sleep(cycle_wait)

        except Exception as e:
            print(f"⚠️ خطأ عام: {e}")
            time.sleep(60)

# (نفس الـ Dashboard البسيط اللي وضعته)
