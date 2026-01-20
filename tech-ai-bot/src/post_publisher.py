import os
import tweepy
import google.genai as genai
import requests
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)

def get_content_from_openrouter(prompt):
    """الخيار الاحتياطي: كوين (OpenRouter) بنفس النمط الاحترافي."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"❌ فشل كوين: {e}")
        return None

def generate_professional_content():
    """توليد محتوى تقني دقيق (نمط LTPO: الأهمية، التوظيف، المصدر)."""
    professional_prompt = (
        "اكتب تغريدة تقنية احترافية جداً باللغة العربية عن موضوع تقني حديث ودقيق.\n"
        "التزم بالتنسيق التالي حرفياً:\n"
        "1. اسم التقنية (بعنوان واضح).\n"
        "2. الأهمية: شرح الفائدة التقنية العميقة.\n"
        "3. التوظيف: نصيحة عملية للمستخدم.\n"
        "4. المصدر: اسم جهة تقنية موثوقة.\n\n"
        "اجعل الأسلوب مقتضباً، مفيداً، وخالياً من الحشو."
    )
    
    try:
        # المحاولة مع جمناي أولاً
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=professional_prompt
        )
        return response.text.strip()
    except Exception as e:
        logging.warning(f"⚠️ جمناي غير متاح حالياً ({e})، جاري الانتقال لـ كوين...")
        return get_content_from_openrouter(professional_prompt)

def publish_tweet():
    try:
        # استخدام Twitter API V2 (الوحيد الذي يعمل حالياً للنشر المجاني)
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        
        content = generate_professional_content()
        
        if content:
            # التأكد من طول التغريدة لسياسة تويتر
            client.create_tweet(text=content[:280])
            logging.info("✅ تم النشر بنجاح بالنمط الاحترافي!")
        else:
            logging.error("❌ لم يتم توليد محتوى للنشر.")
            
    except Exception as e:
        logging.error(f"❌ خطأ في النشر: {e}")

if __name__ == "__main__":
    publish_tweet()
