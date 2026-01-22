import os
import tweepy
import requests
import logging
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv

# إعدادات التسجيل لضمان الـوُضُـوح
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

# إعداد الاتصال بـ X API V2 (نسخة Premium)
client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET"),
    wait_on_rate_limit=True
)

def get_ai_content(prompt):
    """جلب المحتوى من OpenRouter باستخدام أحدث موديلات 2026"""
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.9 # حرارة أعلى قليلاً لمزيد من الإبداع والإثارة
            }
        )
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ خطأ AI: {e}")
        return None

def generate_youth_trend():
    """توليد محتوى احترافي بأسلوب 2026: أرقام، إثارة، وتفاعل"""
    # مواضيع مستلهمة من واقع يناير 2026
    topics = [
        "معالج Snapdragon 8 Gen 5 ودقة 2 نانومتر: هل انتهى عصر التفوق التقني لـ Apple؟",
        "الوكيل الرقمي (AI Agent): كيف سيتولى هاتفك حجز رحلاتك وإدارة عملك في 2026 دون تدخلك؟",
        "وداعاً للـ PC القوي: خدمة GeForce Now RTX 5080 تجعل Cloud Gaming هو المعيار الجديد.",
        "تسريبات Samsung S26 Ultra: كاميرا بدقة 200MP مطورة بالذكاء الاصطناعي الكمي."
    ]
    topic = random.choice(topics)
    
    prompt = (
        f"أنت صانع محتوى تقني عالمي (Influencer) في عام 2026. اكتب مقالاً لـ X Premium عن: {topic}.\n"
        "استخدم القواعد التالية:\n"
        "1. البداية الصادمة: ابدأ بـ 'لغة الأرقام' أو حقيقة تقنية تثير الفضول فوراً.\n"
        "2. الأسلوب: سريع، فصيح، ومثير للتشويق (ممنوع الحشو الممل).\n"
        "3. الـوُضُـوح: استخدم كلمات قوية تعكس ثقتك بالمعلومة.\n"
        "4. التفاعل: اختم بسؤال 'جدلي' يحفز المتابعين على التعليق.\n"
        "5. الطول: لا يتجاوز 750 حرف.\n\n"
        "لا تستخدم مقدمات مثل 'أهلاً بكم'، ادخل في صلب 'الثورة التقنية' فوراً.\n"
        "#تقنية_2026 #AI_Revolution #عُمان #Tech_Trends"
    )
    return get_ai_content(prompt)

def reply_to_mentions():
    """نظام الردود الذكية لرفع رانك الحساب"""
    try:
        me = client.get_me()
        mentions = client.get_users_mentions(id=me.data.id, max_results=5)
        
        if not mentions or not mentions.data:
            logging.info("ℹ️ لا توجد منشنز حالياً.")
            return

        for tweet in mentions.data:
            logging.info(f"💬 جاري الرد على: {tweet.id}")
            reply_prompt = (
                f"أجب بذكاء، فصاحة، وإثارة على هذا التعليق: {tweet.text}\n"
                "اج
