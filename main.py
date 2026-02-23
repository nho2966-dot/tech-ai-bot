import os
import re
import asyncio
import random
import tweepy
import httpx
from loguru import logger
from openai import OpenAI
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ الربط بالخزنة (Secrets)
# ==========================================
X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ==========================================
# 🧠 توليد المحتوى (الأسلوب الخليجي)
# ==========================================
async def generate_apex_content(prompt):
    try:
        client = OpenAI(api_key=OPENAI_KEY)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

# ==========================================
# 🔍 رادار صيد "خفايا التقنية"
# ==========================================
async def get_latest_ai_gem():
    # البحث عن أخبار الأدوات الجديدة والمقارنات
    url = "https://news.google.com/rss/search?q=AI+tools+features+individuals+when:24h&hl=ar&gl=SA&ceid=SA:ar"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, 'xml')
            item = soup.find('item')
            if item: return item.title.text, item.link.text
    except: pass
    return None, None

# ==========================================
# 📢 المهمة التنفيذية
# ==========================================
async def run_mission():
    logger.info("⚡️ فحص الصلاحيات والبدء في التنفيذ...")
    
    # تعريف الكلاينت مع خاصية انتظار قيود المعدل
    client_v2 = tweepy.Client(
        consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
        access_token=X_CRED["at"], access_token_secret=X_CRED["ts"],
        wait_on_rate_limit=True
    )

    # 1. نشر السبق الصحفي (Post)
    headline, link = await get_latest_ai_gem()
    if headline:
        prompt = (
            f"حلل الخبر: ({headline}). اكتب تغريدة خليجية احترافية.\n"
            "التقسيم: 🔹الخبر، ✨الخفايا (ميزة قوية)، 🛠التطبيق (كيف نستخدمها)، 📍الزبدة.\n"
            "استخدم مصطلحات إنجليزية (بين قوسين). لا تذكر أنك بوت."
        )
        content = await generate_apex_content(prompt)
        if content:
            client_v2.create_tweet(text=f"{content}\n\n🔗 {link}")
            logger.success("✅ تم نشر التغريدة بنجاح!")

    # 2. نظام الردود (Replies) - محمي من التوقف
    try:
        me = client_v2.get_me()
        mentions = client_v2.get_users_mentions(id=me.data.id, max_results=5)
        if mentions.data:
            for tweet in mentions.data:
                reply_prompt = f"رد كخبير تقني خليجي بلمحة ذكية على: ({tweet.text})"
                reply_text = await generate_apex_content(reply_prompt)
                if reply_text:
                    client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    logger.success(f"💬 تم الرد على المنشن {tweet.id}")
    except Exception as e:
        logger.warning(f"⚠️ نظام الردود واجه قيداً مؤقتاً: {e}")

if __name__ == "__main__":
    asyncio.run(run_mission())
