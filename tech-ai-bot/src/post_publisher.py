import os
import requests
import tweepy
import random
from google import genai
import logging
import hashlib
import time

# 1. إعداد نظام التسجيل الاحترافي
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ملف منع التكرار لضمان عدم نشر نفس المعلومة مرتين
LAST_HASH_FILE = "last_hash.txt"

def get_content_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    current_hash = get_content_hash(content)
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
            last_hash = f.read().strip()
        if current_hash == last_hash:
            logging.info("⚠️ محتوى مكرر تم رصده — جاري الإلغاء لتجنب إزعاج المتابعين.")
            return True
    with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)
    return False

def generate_content_from_gemini():
    """توليد محتوى متنوع (أخبار، نقاش، نصائح) لجذب المتابعين."""
    try:
        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            return None, None
        
        client = genai.Client(api_key=api_key)

        # ركائز المحتوى (Content Pillars) لضمان نمو الحساب
        topics = [
            "خبر تقني عاجل ومذهل حدث في 2026 مع توضيح كيف سيغير حياتنا.",
            "سؤال تفاعلي وجدلي حول مستقبل الذكاء الاصطناعي لتحفيز الناس على الرد والتعليق.",
            "أداة ذكاء اصطناعي سرية أو نصيحة تقنية تزيد الإنتاجية بنسبة 200%.",
            "توقع تقني جريء لعام 2027 وما بعده بناءً على إنجازات اليوم."
        ]
        
        selected_topic = random.choice(topics)
        
        prompt = f"""
        أنت خبير ومؤثر تقني (Tech Influencer) على منصة X. 
        اكتب تغريدة احترافية عن: {selected_topic}
        
        الهدف: الحصول على أكبر قدر من المتابعين والردود.
        الشروط:
        1. ابدأ بـ 'Hook' (جملة افتتاحية) قوية جداً تخطف العين.
        2. استخدم لغة عربية فصحى عصرية، مشوقة وبسيطة.
        3. اختم دائماً بسؤال ذكي يحفز المتابعين على كتابة تعليق.
        4. أضف إيموجي مناسباً و3 هاشتاقات تقنية قوية.
        5. لا تتجاوز 280 حرفاً.
        """
        
        # إضافة آلية إعادة المحاولة عند حدوث خطأ 429 (الزحام)
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt
                )
                if response and response.text:
                    return response.text.strip(), "https://gemini.google.com/"
            except Exception as e:
                if "429" in str(e):
                    logging.warning("⚠️ زحام في Gemini، الانتظار 30 ثانية قبل المحاولة...")
                    time.sleep(30)
                    continue
                raise e
        return None, None
    except Exception as e:
        logging.error(f"❌ فشل Gemini: {e}")
        return None, None

def generate_content_from_openrouter():
    """خطة بديلة (OpenRouter) في حال فشل Gemini تماماً."""
    try:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key: return None, None
        
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "اكتب تغريدة تقنية عربية مشوقة جداً عن الذكاء الاصطناعي مع سؤال تفاعلي."}]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=15)
        return res.json()["choices"][0]["message"]["content"].strip(), "https://openrouter.ai/"
    except:
        return None, None

def publish_tech_tweet():
    """الدالة المركزية للنشر."""
    logging.info("🚀 انطلاق عملية توليد المحتوى الجاذب...")
    try:
        # محاولة توليد المحتوى بالترتيب: Gemini -> OpenRouter -> Fallback
        content, source = generate_content_from_gemini()
        if not content:
            content, source = generate_content_from_openrouter()
        if not content:
            fallbacks = [
                "الذكاء الاصطناعي في 2026 يعيد صياغة مفهوم الإبداع. هل أنتم مستعدون للمستقبل؟ 🚀 #AI #تقنية",
                "أدوات AI الجديدة تجعل المستحيل ممكناً. ما هي أكثر أداة أبهرتكم هذا العام؟ 🧠 #الذكاء_الاصطناعي"
            ]
            content, source = random.choice(fallbacks), "https://tech-bot.ai"

        if is_duplicate(content):
            return

        # إعداد عميل X
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # النشر الفعلي
        client.create_tweet(text=content[:280])
        logging.info("✅ تم النشر بنجاح! التغريدة الآن تجذب المتابعين على X.")

    except Exception as e:
        logging.error(f"❌ خطأ في مهمة النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
