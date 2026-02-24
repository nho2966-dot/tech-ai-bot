import os
import asyncio
import random
from loguru import logger
import tweepy
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ⚙️ الربط المباشر (OAuth 1.0a User Context)
# ==========================================
def get_x_client():
    # نستخدم الطريقة التقليدية لأنها الأكثر استقراراً للنشر
    return tweepy.Client(
        bearer_token=os.getenv("X_BEARER_TOKEN"),
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
        wait_on_rate_limit=True
    )

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (أيبكس)
# ==========================================
async def ai_guard(prompt):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
    sys_prompt = "أنت 'أيبكس'. خبير ذكاء اصطناعي خليجي. لا تذكر 'الثورة الصناعية' نهائياً."
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except: return "SKIP"

# ==========================================
# 📰 محرك النشر (مع فحص حي للتكرار)
# ==========================================
async def run_apex():
    try:
        client = get_x_client()
        me = client.get_me()
        logger.success(f"✅ متصل كـ: {me.data.username}")

        # جلب الأخبار
        async with httpx.AsyncClient() as c:
            r = await c.get("https://aitnews.com/feed/", timeout=15)
            items = BeautifulSoup(r.content, 'xml').find_all('item')

        # فحص آخر التغريدات (منع التكرار الفادح)
        my_tweets = client.get_users_tweets(id=me.data.id, max_results=10)
        history = [t.text for t in my_tweets.data] if my_tweets.data else []

        for item in items:
            link = item.link.text
            if any(link in h for h in history):
                continue # الخبر منشور، نتخطاه
            
            tweet_txt = await ai_guard(item.title.text)
            if "SKIP" not in tweet_txt:
                # محاولة النشر
                client.create_tweet(text=f"{tweet_txt}\n\n🔗 {link}")
                logger.success(f"🚀 تم النشر بنجاح: {item.title.text}")
                return # نكتفي بخبر واحد في كل تشغيلة لـ GitHub Actions
                
    except Exception as e:
        logger.error(f"❌ الخطأ الفعلي: {e}")

if __name__ == "__main__":
    asyncio.run(run_apex())
