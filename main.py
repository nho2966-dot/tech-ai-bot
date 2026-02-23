import os
import re
import asyncio
import random
import tweepy
import httpx
import telegram
from datetime import datetime
from loguru import logger
from google import genai
from openai import OpenAI
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ الإعدادات (Secrets)
# ==========================================
KEYS = {"GEMINI": os.getenv("GEMINI_KEY"), "OPENAI": os.getenv("OPENAI_API_KEY"), "GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {"ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"), "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")}
TG_CONFIG = {"token": os.getenv("TG_TOKEN"), "chat_id": os.getenv("TELEGRAM_CHAT_ID")}

# ==========================================
# 🧠 عقل "أيبكس" (Intelligence Engine)
# ==========================================
async def smart_fetch_content(prompt):
    brains = [
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content)
    ]
    for name, func in brains:
        try:
            if not KEYS.get(name.upper()): continue
            content = await asyncio.to_thread(func, prompt)
            if content and len(content) > 30:
                return re.sub(r'[àâçéèêëîïôûùüÿñæœ\u3040-\u309F\u0E00-\u0E7F]', '', content).strip(), name
        except: continue
    return None, None

# ==========================================
# 🔍 رادار الأخبار (Google News RSS)
# ==========================================
async def fetch_insider_news():
    rss_url = "https://news.google.com/rss/search?q=AI+tools+individuals+features+when:24h&hl=ar&gl=SA&ceid=SA:ar"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(rss_url)
            soup = BeautifulSoup(r.text, 'xml')
            items = soup.find_all('item')
            for item in items:
                title, link = item.title.text, item.link.text
                if len(title) > 55: return title, link
    except: pass
    return None, None

# ==========================================
# 📢 مهمة النشر (The Post)
# ==========================================
async def apex_post_mission(client_v2):
    try:
        headline, source_link = await fetch_insider_news()
        if not headline: return

        prompt = (
            f"حلل الخبر التقني: ({headline}).\n"
            "اكتب تغريدة بشرية خليجية فخمة: 🔹الخبر بعمق، ✨الخفايا، 🛠الجانب التطبيقي، 📍الزبدة.\n"
            "أسلوب خبير، مصطلحات إنجليزية بين قوسين، لا تذكر أنك بوت."
        )
        content, brain = await smart_fetch_content(prompt)
        if content:
            final_tweet = f"{content}\n\n🔗 المصدر:\n{source_link}"
            client_v2.create_tweet(text=final_tweet)
            logger.success(f"🔥 نُشر السبق عبر {brain}")
            if TG_CONFIG["token"]:
                try: await telegram.Bot(TG_CONFIG["token"]).send_message(TG_CONFIG["chat_id"], final_tweet)
                except: pass
    except Exception as e: logger.error(f"Post Error: {e}")

# ==========================================
# 💬 مهمة الردود (The Reply) - نسخة V2 المستقرة
# ==========================================
async def apex_reply_mission(client_v2):
    try:
        my_id = client_v2.get_me().data.id
        # البحث عن المنشنات فقط لضمان عدم الحظر وتجاوز خطأ 401
        mentions = client_v2.get_users_mentions(id=my_id, max_results=5)
        
        if mentions.data:
            for tweet in mentions.data:
                reply_prompt = f"رد كخبير تقني خليجي على: ({tweet.text}). أسلوب بشري وودود."
                reply_content, _ = await smart_fetch_content(reply_prompt)
                if reply_content:
                    client_v2.create_tweet(text=reply_content, in_reply_to_tweet_id=tweet.id)
                    logger.success(f"💬 تم الرد على المنشن: {tweet.id}")
                    await asyncio.sleep(30)
    except Exception as e: logger.warning(f"Reply system skipped: {e}")

# ==========================================
# ⏳ المحرك الرئيسي
# ==========================================
async def main():
    logger.info("🚀 انطلاق أيبكس المطور")
    client_v2 = tweepy.Client(
        consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
        access_token=X_CRED["at"], access_token_secret=X_CRED["ts"]
    )
    
    # تنفيذ المهام بشكل مستقل لضمان الاستمرارية
    await apex_post_mission(client_v2)
    await apex_reply_mission(client_v2)

if __name__ == "__main__":
    asyncio.run(main())
