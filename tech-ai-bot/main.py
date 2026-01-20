import os
import tweepy
import google.genai as genai
import requests
import logging
import hashlib
import random
from dotenv import load_dotenv

# 1. الإعدادات العامة
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    try:
        if os.path.exists(LAST_HASH_FILE):
            with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
                if f.read().strip() == current_hash:
                    logging.info("🚫 محتوى مكرر — تم إلغاء الدورة.")
                    return True
        with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
            f.write(current_hash)
        return False
    except:
        return False

# 2. محرك التوليد الشامل (بدون حصر)
def generate_broad_tech_content():
    # توسيع المصادر لتشمل تخصصات متنوعة
    sources = [
        "MIT Technology Review", "IEEE Spectrum", "NASA Tech", "Scientific American",
        "The Verge", "TechCrunch", "Ars Technica", "ZDNet", "Hacker News"
    ]
    
    # اختيار تصنيف عشوائي في كل مرة لضمان التنوع
    topics = ["الذكاء الاصطناعي", "الأمن السيبراني", "تقنيات الفضاء", "الحوسبة الكمية", "إنترنت الأشياء", "الهواتف والعتاد", "الطاقة المتجددة"]
    selected_source = random.choice(sources)
    selected_topic = random.choice(topics)

    prompt = (
        f"اكتب تغريدة احترافية عن جديد {selected_topic} بناءً على تقارير من {selected_source}.\n"
        "الهيكل:\n"
        "🛡️ التقنية: (اسم الابتكار)\n"
        "💡 الأهمية: (لماذا يغير هذا الابتكار قواعد اللعبة؟ استخدم لغة الأرقام)\n"
        "🛠️ التوظيف: (نصيحة عملية أو استشراف للمستقبل)\n"
        "🌍 المصدر: [" + selected_source + "]\n"
        "الشروط: لغة عربية فصحى، معلومات حقيقية 100%، وأقل من 270 حرفاً."
    )

    try:
        # المحاولة عبر كوين (Llama 3.1 70B) للرصانة العلمية
        headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-3.1-70b-instruct", 
            "messages": [{"role": "system", "content": "أنت موسوعة تقنية عالمية تنشر الأخبار الموثقة فقط."}, {"role": "user", "content": prompt}], 
            "temperature": 0.4
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=25)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
    except:
        pass

    try:
        # بديل جمناي
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except:
        return None

# 3. وظيفة النشر (باستخدام OAuth 1.0a لضمان الصلاحيات)
def publish_tweet():
    logging.info("🚀 بدء دورة الاستكشاف التقني الشامل...")
    content = generate_broad_tech_content()
    
    if not content or is_duplicate(content):
        return

    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر الشامل بنجاح!")
    except Exception as e:
        logging.error(f"❌ خطأ النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
