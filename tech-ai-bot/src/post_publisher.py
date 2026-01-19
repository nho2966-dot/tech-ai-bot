import os
import tweepy
import logging
import re
import random
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)

def smart_truncate(content, length=280):
    if len(content) <= length: return content
    truncated = content[:length-3]
    last_punctuation = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('؟'))
    if last_punctuation > length * 0.7:
        return content[:last_punctuation + 1]
    return truncated.rsplit(' ', 1)[0] + "..."

def get_pro_tips():
    tips = [
        {
            "ar": "🎯 تقنية RAG في الذكاء الاصطناعي\n💡 الأهمية: تمنع 'الهلوسة' بربط AI بمصادرك.\n🛠️ توظيفها: اربط ملفاتك بـ LLM للحصول على نتائج دقيقة.\n🔗 المصدر: IBM",
            "en": "🎯 RAG in AI\n💡 Importance: Prevents hallucinations by grounding AI in your data.\n🛠️ Practice: Connect docs to LLMs for accurate results.\n🔗 Source: IBM"
        }
    ]
    selected = random.choice(tips)
    return f"{selected['ar']}\n\n{selected['en']}\n\n#AI #Tech"

def publish_tech_tweet():
    try:
        client = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
        )
        
        # هنا يمكنك إضافة دالة Gemini لجلب أخبار حية كما في الأكواد السابقة
        content = get_pro_tips() 
        final_tweet = smart_truncate(content)
        
        client.create_tweet(text=final_tweet)
        logging.info("✅ تم النشر بنجاح!")
    except Exception as e:
        logging.error(f"❌ فشل النشر: {e}")

if __name__ == "__main__":
    publish_tech_tweet()
