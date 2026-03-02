import os
import asyncio
import httpx
import tweepy
import sqlite3
import hashlib
import random
import re
import difflib
from datetime import datetime
from loguru import logger

# =========================================================
# 🔐 الإعدادات والمفاتيح
# =========================================================
GEMINI_KEY = os.getenv("GEMINI_KEY")
X_CONFIG = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

client_v2 = tweepy.Client(
    bearer_token=X_CONFIG["bearer"],
    consumer_key=X_CONFIG["key"], consumer_secret=X_CONFIG["secret"],
    access_token=X_CONFIG["token"], access_token_secret=X_CONFIG["access_s"],
    wait_on_rate_limit=True
)

# =========================================================
# 🗄️ قاعدة البيانات المطورة (حفظ الأفكار)
# =========================================================
conn = sqlite3.connect("nasser_sovereign_v2.db")
cursor = conn.cursor()
# إضافة عمود 'topic_idea' لحفظ جوهر الفكرة ومنع تكرارها معنوياً
cursor.execute("""
    CREATE TABLE IF NOT EXISTS published (
        hash TEXT PRIMARY KEY, 
        topic_idea TEXT, 
        content_text TEXT, 
        date TEXT
    )
""")
conn.commit()

# =========================================================
# 🛡️ فلتر ناصر ومنع التكرار المعنوي
# =========================================================
def nasser_filter(text):
    if not text: return ""
    # الالتزام بمصطلحات الأفراد والذكاء الاصطناعي
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    # حذف أي ذكر لاسم ناصر أو كلمة خبير لضمان السرية والمهنية
    text = re.sub(r'\b(ناصر|خبير|بوت|آلي)\b', '', text)
    return text.strip()

def is_intellectually_duplicated(new_idea, threshold=0.45):
    """
    مقارنة الفكرة الجديدة بكل ما نُشر سابقاً.
    إذا زادت نسبة التشابه المعنوي عن 45% يعتبر مكرراً.
    """
    cursor.execute("SELECT topic_idea FROM published")
    past_ideas = [row[0] for row in cursor.fetchall()]
    
    for old_idea in past_ideas:
        similarity = difflib.SequenceMatcher(None, new_idea, old_idea).ratio()
        if similarity > threshold:
            return True, similarity
    return False, 0

# =========================================================
# 🧠 محرك التوليد (Gemini)
# =========================================================
async def generate_scoop(prompt, system_msg):
    url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers = {"Authorization": f"Bearer {GEMINI_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "model": "gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ]
            }
            r = await client.post(url, headers=headers, json=payload)
            return nasser_filter(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        logger.error(f"❌ خطأ في محرك الذكاء الاصطناعي: {e}")
        return None

# =========================================================
# 🐦 وظيفة النشر الأساسية
# =========================================================
async def post_unique_thread():
    # 1. اختيار موضوع عشوائي من "الخبايا"
    scoop_topics = [
        "خبايا استخدام أدوات AI لتحويل النص إلى فيديو سينمائي للأفراد.",
        "تسريب ميزات البرمجة الجديدة في نماذج الذكاء الاصطناعي.",
        "طريقة مخفية لدمج ChatGPT مع ملفاتك الشخصية دون رفعها للسحاب.",
        "أدوات AI تتيح للأفراد بناء تطبيقات كاملة في دقائق."
    ]
    selected_topic = random.choice(scoop_topics)

    # 2. توليد المحتوى
    system = "أنت مصدر تقني عالمي متخصص في خبايا الذكاء الاصطناعي للأفراد. أسلوبك خليجي، دقيق، ولا يذكر الأسماء الشخصية."
    prompt = f"اكتب ثريد من 3 تغريدات عن: {selected_topic}. ركز على القيمة المضافة."
    
    raw_content = await generate_scoop(prompt, system)
    if not raw_content: return

    # 3. استخراج "بصمة الفكرة" لمنع التكرار المعنوي
    idea_prompt = f"لخص الفكرة الجوهرية لهذا النص في 4 كلمات فقط: {raw_content}"
    core_idea = await generate_scoop(idea_prompt, "أنت محلل محتوى.")

    # 4. التحقق من التكرار (حتى لو تغيرت الصياغة)
    is_dup, score = is_intellectually_duplicated(core_idea)
    if is_dup:
        logger.warning(f"🚫 تم إلغاء النشر! الفكرة مكررة بنسبة {score:.2f}. (الفكرة: {core_idea})")
        return

    # 5. النشر على X
    tweets = [t.strip() for t in raw_content.split('\n\n') if len(t) > 10]
    try:
        last_id = None
        for i, tweet_text in enumerate(tweets[:3]):
            if i == 0:
                response = client_v2.create_tweet(text=tweet_text)
            else:
                response = client_v2.create_tweet(text=tweet_text, in_reply_to_tweet_id=last_id)
            last_id = response.data['id']
            await asyncio.sleep(random.randint(20, 40)) # أنسنة التوقيت

        # 6. حفظ "بصمة الفكرة" في القاعدة لمنع تكرارها مستقبلاً
        content_hash = hashlib.md5(raw_content.encode()).hexdigest()
        cursor.execute("INSERT INTO published VALUES (?,?,?,?)", 
                       (content_hash, core_idea, raw_content, datetime.now().isoformat()))
        conn.commit()
        logger.success(f"✅ تم نشر خبيئة تقنية جديدة: {core_idea}")

    except Exception as e:
        logger.error(f"❌ فشل النشر: {e}")

# =========================================================
# 🚀 تشغيل المهمة
# =========================================================
if __name__ == "__main__":
    logger.info("🚀 انطلاق بوت ناصر لمنع التكرار المعنوي...")
    asyncio.run(post_unique_thread())
