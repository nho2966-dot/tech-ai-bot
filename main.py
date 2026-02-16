import time
import logging
import sqlite3
from datetime import datetime
from google import genai
import openai

# ===================== إعدادات Logging =====================
logging.basicConfig(
    level=logging.INFO,
    format="🛡️ %(asctime)s - %(levelname)s - %(message)s"
)

# ===================== إعدادات العملاء =====================
gemini_client = genai.TextClient()  # جوك
openai.api_key = "YOUR_OPENAI_API_KEY"  # كوين

# ===================== إعدادات قاعدة البيانات =====================
DB_FILE = "published_content.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            model_used TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ===================== قائمة الكلمات المفتاحية =====================
KEYWORDS = [
    "مساعدات الذكاء الاصطناعي الشخصية",
    "أحدث التطبيقات الذكية",
    "تقنيات الواقع الافتراضي"
]

# ===================== دوال النشر =====================
class ResourceExhaustedError(Exception):
    pass

def call_gemini(prompt):
    try:
        response = gemini_client.generate_content(
            model="gemini-2.0-flash",
            prompt=prompt
        )
        return response.output_text
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            raise ResourceExhaustedError("حصة Gemini انتهت أو تجاوزت الحد")
        else:
            raise e

def call_openai(prompt, model="gpt-4o-mini"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def save_to_db(keyword, model_used, content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posts (keyword, model_used, content) VALUES (?, ?, ?)",
        (keyword, model_used, content)
    )
    conn.commit()
    conn.close()

def generate_content(prompt, retries=3):
    """تسلسل هرمي: Gemini → OpenAI → OpenAI GPT-4o احتياطي"""
    attempt = 0
    while attempt < retries:
        try:
            logging.info(f"🚀 محاولة النشر عبر Gemini: '{prompt}'")
            content = call_gemini(prompt)
            save_to_db(prompt, "Gemini", content)
            return content
        except ResourceExhaustedError:
            logging.warning("💡 حصة Gemini انتهت، استخدام OpenAI كبديل...")
            try:
                content = call_openai(prompt)
                save_to_db(prompt, "OpenAI GPT-4o-mini", content)
                return content
            except Exception as e:
                logging.error(f"❌ خطأ OpenAI: {e}")
        except Exception as e:
            logging.error(f"❌ خطأ غير متوقع: {e}")
        
        attempt += 1
        backoff = 2 ** attempt
        logging.info(f"⏳ انتظار {backoff}s قبل إعادة المحاولة...")
        time.sleep(backoff)

    # fallback احتياطي نهائي
    logging.info("🔁 إعادة المحاولة النهائية باستخدام OpenAI GPT-4o")
    content = call_openai(prompt, model="gpt-4o")
    save_to_db(prompt, "OpenAI GPT-4o-fallback", content)
    return content

# ===================== حلقة النشر =====================
def run_bot():
    init_db()
    for keyword in KEYWORDS:
        logging.info(f"🛡️ معالجة الكلمة المفتاحية للنشر: {keyword}")
        content = generate_content(keyword)
        logging.info(f"✅ المحتوى المنشور:\n{content}\n")
        # استراحة قصيرة لتجنب الحظر
        time.sleep(5)

if __name__ == "__main__":
    run_bot()
