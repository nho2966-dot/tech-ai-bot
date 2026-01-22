import os
import tweepy
import requests
import logging
import random
import re
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv

# ✅ إعدادات النخبة والـوُضُـوح
load_dotenv()
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [MASTER-AI] - %(message)s',
    handlers=[logging.FileHandler("cyber_hunter.log"), logging.StreamHandler()]
)

# ✅ تهيئة الوصول لمنصة X
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

ARCHIVE_FILE = "published_archive.txt"

# ---------------------------------------------------------
# 1. بروتوكولات الذكاء الاصطناعي المتعددة (Multi-Protocol AI)
# ---------------------------------------------------------
def generate_master_content(scenario):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # حقن الشخصية والصرامة والمصادر النخبوية
        system_instructions = (
            f"أنت 'Cyber Hunter' - خبير استخبارات تقنية عالمي. الوقت: {current_time}.\n"
            "⚠️ بروتوكول العمل:\n"
            "1. المصادر: أبحاث (Mandiant, Gartner)، حسابات موثقة، تسريبات GitHub، ومؤتمرات (Black Hat).\n"
            "2. الصرامة: ممنوع الكلام العائم. اذكر أسماء، أرقام إصدارات، CVEs، أو مواصفات تقنية دقيقة.\n"
            f"3. المهمة الحالية: {scenario['instruction']}\n"
            "4. الهيكل: [TITLE: ناري] -> الخطاف (3 ثواني) -> الزبدة (3 نقاط) -> تلميحة للمحترفين -> 🔗 المصدر -> #هاشتاج."
        )

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "system", "content": system_instructions},
                             {"role": "user", "content": "حلل وانشر أحدث سبق صحفي مـوُثـوُق."}],
                "temperature": 0.4
            }
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ فشل المحرك: {e}")
        return None

# ---------------------------------------------------------
# 2. نظام الفلترة والأرشفة (منع التكرار والحشو)
# ---------------------------------------------------------
def is_duplicate(title):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return title.lower()[:60] in f.read().lower()

def save_to_archive(title):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().date()}: {title}\n")

# ---------------------------------------------------------
# 3. مـوُلد الهوية البصرية (Visual Engine)
# ---------------------------------------------------------
def get_visual(keyword):
    path = "v_id.jpg"
    try:
        # البحث عن صور تقنية داكنة واحترافية
        url = f"https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80&keywords={keyword},cyberpunk"
        img_res = requests.get(url, timeout=10)
        with open(path, "wb") as f: f.write(img_res.content)
        media = api_v1.media_upload(filename=path)
        return media.media_id, path
    except: return None, None

# ---------------------------------------------------------
# 4. معالج النشر والتحقق (The Publisher)
# ---------------------------------------------------------
def run_agent():
    oman_tz = pytz.timezone('Asia/Muscat')
    now = datetime.now(oman_tz)
    
    # قائمة السيناريوهات النخبوية المدمجة
    scenarios = [
        {"cat": "cyber", "instruction": "رصد اختراق نشط أو ثغرة Zero-day مع خطوات حماية فورية 🚨"},
        {"cat": "leaks", "instruction": "تحليل كود مسرب أو ميزة مخفية في بيتا (WhatsApp, X, iOS)"},
        {"cat": "hardware", "instruction": "مقارنة معالجات قادمة (NVIDIA, Apple M-series) بلغة الأداء الفعلي"},
        {"cat": "fact-check", "instruction": "كشف حقيقة إشاعة تقنية منتشرة بناءً على تقارير Bloomberg/Reuters"}
    ]
    
    selected = random.choice(scenarios)
    content = generate_master_content(selected)
    
    if not content or "TITLE:" not in content: return

    # استخراج العنوان والتحقق من الصرامة والتوثيق
    title = re.search(r"TITLE: (.*)\n", content).group(1).strip()
    if is_duplicate(title) or "http" not in content:
        logging.warning(f"🚫 تم الرفض: خبر مكرر أو غير مـوُثـوُق برابط.")
        return

    post_text = content.replace(f"TITLE: {title}", "").strip()
    media_id, img_path = get_visual(selected["cat"])

    try:
        client.create_tweet(text=post_text[:280], media_ids=[media_id] if media_id else None)
        save_to_archive(title)
        logging.info(f"✅ تم نشر مـوُضـوُع نخبة: {title}")
    finally:
        if img_path and os.path.exists(img_path): os.remove(img_path)

# ---------------------------------------------------------
# 5. التوقيت الذكي المستمر (24/7 Monitoring)
# ---------------------------------------------------------
if __name__ == "__main__":
    logging.info("🤖 Cyber Hunter Master Agent is LIVE...")
    while True:
        oman_now = datetime.now(pytz.timezone('Asia/Muscat'))
        # النشر في ساعات الذروة التقنية لضمان التفاعل
        if oman_now.hour in [9, 12, 16, 20, 22] and oman_now.minute == 0:
            run_agent()
            time.sleep(65)
        time.sleep(30)
