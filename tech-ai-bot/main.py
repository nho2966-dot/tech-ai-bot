import os
import requests
import logging
import random
from datetime import datetime # إضافة التاريخ لكسر التكرار
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

def generate_tech_content():
    # 1. الحصول على تاريخ اليوم وتحديد موضوع عشوائي لضمان التجديد
    today = datetime.now().strftime("%Y-%m-%d")
    topics = ["الذكاء الاصطناعي", "الأمن السيبراني", "الهواتف الذكية", "الفضاء", "الحوسبة الكمية", "السيارات الكهربائية"]
    selected_topic = random.choice(topics)
    
    sources = ["The Verge", "TechCrunch", "Wired", "GSMArena", "MIT Tech Review"]
    source = random.choice(sources)
    
    # 2. تحديث البرومبت ليشمل التاريخ والموضوع المحدد
    # أضفنا تعليمات صارمة للنموذج بعدم تكرار الأخبار القديمة
    prompt = (
        f"التاريخ اليوم هو {today}. اكتب خبر تقني حقيقي وجديد كلياً عن {selected_topic} من مصدر {source}.\n"
        "يجب أن تكون التغريدة فريدة ومختلفة عن أي تغريدة سابقة.\n"
        "الهيكل المطلوب:\n"
        "🛡️ التقنية: (اسم الابتكار)\n"
        "💡 الأهمية: (الفائدة بلغة الأرقام)\n"
        "🛠️ التوظيف: (نصيحة للمستخدم)\n"
        f"🌍 المصدر: {source}\n"
        "#تقنية #أخبار"
    )
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", 
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct", 
                "messages": [{"role": "user", "content": prompt}], 
                "temperature": 0.9, # زيادة الحرارة لزيادة الإبداع وتقليل التكرار
                "top_p": 0.9
            }
        )
        response_data = res.json()
        return response_data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"خطأ في التوليد: {e}")
        return None

# باقي الكود (publish_tweet) يبقى كما هو...
