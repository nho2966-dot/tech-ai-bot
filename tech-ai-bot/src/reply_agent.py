import os
import tweepy
import logging
from google import genai
from openai import OpenAI
import re

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO)

def clean_reply(text):
    """تنظيف الرد لضمان عدم تجاوز حدود X."""
    if not text: return ""
    cleaned = re.sub(r'[^\u0600-\u06FF\s0-9\.\?\!\,\:\-\#\(\)a-zA-Z🐦🤖🚀💡✨🧠🌍📱💻⌚📊📈🔋🚨🔗🎯🛠️]', '', text)
    return cleaned[:280]

def generate_smart_reply(comment_text):
    """توليد رد تقني ذكي باستخدام Gemini مع fallback لـ Qwen."""
    prompt = f"أجب على هذا التعليق التقني بلباقة (عربي وإنجليزي) مع توضيح الفائدة العملية: {comment_text}"
    
    # المحاولة 1: Gemini
    try:
        api_key = os.getenv("GEMINI_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return clean_reply(response.text.strip())
    except Exception as e:
        logging.error(f"⚠️ Gemini Reply Error: {e}")

    # المحاولة 2: Qwen (B-plan)
    try:
        api_key = os.getenv("QWEN_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            completion = client.chat.completions.create(
                model="qwen-2.5-32b",
                messages=[{"role": "user", "content": prompt}]
            )
            return clean_reply(completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"⚠️ Qwen Reply Error: {e}")
        
    return "شكراً لتفاعلك! نحن هنا لدعم رحلتك التقنية. 🚀 | Thanks for your interaction!"

def run_reply_agent():
    """المحرك الرئيسي لمراقبة التعليقات والرد عليها."""
    try:
        # إعداد عميل Twitter (V2)
        client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )
        
        # 1. جلب معرف البوت (ID)
        me = client.get_me().data
        if not me: return

        # 2. جلب آخر الردود (Mentions)
        mentions = client.get_users_mentions(id=me.id, max_results=10)
        
        if not mentions.data:
            logging.info("😴 لا توجد إشارات جديدة حالياً.")
            return

        for tweet in mentions.data:
            logging.info(f"🔍 معالجة التعليق: {tweet.text}")
            
            # منع البوت من الرد على نفسه في حلقة مفرغة
            # (سيتم التحقق من الردود التي لم يتم الرد عليها مسبقاً)
            
            reply_text = generate_smart_reply(tweet.text)
            client.create_tweet(
                text=reply_text,
                in_reply_to_tweet_id=tweet.id
            )
            logging.info(f"✅ تم الرد على التغريدة رقم: {tweet.id}")

    except Exception as e:
        logging.error(f"❌ خطأ حرج في عميل الردود: {e}")

if __name__ == "__main__":
    run_reply_agent()
