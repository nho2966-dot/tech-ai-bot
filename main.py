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
# ⚙️ الإعدادات والسيادة (Secrets)
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY")
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}

TG_CONFIG = {
    "token": os.getenv("TG_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID")
}

# ==========================================
# 🧠 عقل "المحلل التقني" (Multi-Brain System)
# ==========================================
async def smart_fetch_content(prompt):
    brains = [
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Gemini", lambda p: genai.Client(api_key=KEYS["GEMINI"]).models.generate_content(model="gemini-2.0-flash", contents=p).text)
    ]
    
    for name, func in brains:
        try:
            if not KEYS.get(name.upper()) and name != "Gemini": continue
            logger.info(f"🔄 محاولة التوليد عبر: {name}")
            content = await asyncio.to_thread(func, prompt)
            if content and len(content) > 40:
                # تنظيف النص من أي كلمات أعجمية غريبة (مثل mới)
                content = re.sub(r'[àâçéèêëîïôûùüÿñæœ\u3040-\u309F\u0E00-\u0E7F]', '', content)
                return content.strip(), name
        except Exception as e:
            logger.warning(f"⚠️ {name} واجه مشكلة: {e}")
            continue
    return None, None

# ==========================================
# 🔍 رادار البحث العالمي عن الخبايا والمميزات
# ==========================================
async def fetch_insider_news():
    queries = [
        "AI tools hidden features for individuals 2026",
        "best AI productivity hacks comparison",
        "new AI features latest update value add",
        "الذكاء الاصطناعي للأفراد مميزات خفية"
    ]
    query = random.choice(queries)
    # البحث في أخبار آخر 24 ساعة لضمان الطزاجة
    rss_url = f"https://news.google.com/rss/search?q={query}+when:24h&hl=ar&gl=SA&ceid=SA:ar"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(rss_url)
            soup = BeautifulSoup(r.text, 'xml')
            items = soup.find_all('item')
            valid_articles = []
            for item in items:
                title = item.title.text
                link = item.link.text
                if len(title) > 55 and not any(x in title for x in ["نشرة", "لديكم خبر"]):
                    valid_articles.append((title, link))
            if valid_articles:
                return random.choice(valid_articles)
    except Exception as e:
        logger.error(f"News Hunter Error: {e}")
    return None, None

# ==========================================
# 🚀 مهمة النشر الاستهدافي (The Insider)
# ==========================================
async def apex_post_mission():
    try:
        headline, source_link = await fetch_insider_news()
        if not headline: return

        prompt = (
            f"أنت خبير تقني خليجي متمكن. حلل هذا الخبر: ({headline}).\n\n"
            "اكتب تغريدة بشرية فخمة ومقسمة كالتالي:\n"
            "🔹 الخبر بعمق: (اشرح الميزة الجديدة أو التحديث بذكاء).\n\n"
            "✨ الخفايا والمميزات:\n"
            "• (ميزة خفية أو نقطة قوة تفرقه عن المنافسين).\n\n"
            "🛠 الجانب التطبيقي:\n"
            "• (كيف المتابع يستخدم هالأداة أو الميزة الحين؟).\n\n"
            "📍 الزبدة: (سطر واحد يختصر القيمة المضافة للفرد).\n\n"
            "قواعد: أسلوب بشري، لا تذكر أنك بوت، مصطلحات إنجليزية بين قوسين، لا حشو."
        )
        
        content, brain_name = await smart_fetch_content(prompt)
        
        if content:
            final_tweet = f"{content}\n\n🔗 المصدر الموثوق:\n{source_link}"
            api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                                   access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
            api_v2.create_tweet(text=final_tweet)
            logger.success(f"✅ تم النشر (خبايا وتطبيق) عبر {brain_name}")
            
            if TG_CONFIG["token"]:
                try:
                    bot = telegram.Bot(token=TG_CONFIG["token"])
                    await bot.send_message(chat_id=TG_CONFIG["chat_id"], text=final_tweet)
                except: pass
    except Exception as e:
        logger.error(f"Post Mission Error: {e}")

# ==========================================
# 💬 نظام الردود الذكية (Smart Interactions)
# ==========================================
async def apex_reply_mission():
    try:
        auth = tweepy.OAuth1UserHandler(X_CRED["ck"], X_CRED["cs"], X_CRED["at"], X_CRED["ts"])
        api_v1 = tweepy.API(auth)
        api_v2 = tweepy.Client(consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
                               access_token=X_CRED["at"], access_token_secret=X_CRED["ts"])
        
        my_id = api_v2.get_me().data.id
        # جلب المنشورات التي تم منشنة البوت فيها أو كلمات مفتاحية تهمنا
        query = "أفضل أداة ذكاء اصطناعي OR مساعدة تقنية -is:retweet"
        tweets = api_v2.search_recent_tweets(query=query, max_results=10)
        
        if tweets.data:
            for tweet in tweets.data:
                # تجنب الرد على النفس أو التكرار
                if tweet.author_id == my_id: continue
                
                reply_prompt = (
                    f"بصفتك خبير تقني خليجي، رد على هذه التغريدة: ({tweet.text}).\n"
                    "اجعل الرد ذكياً، مختصراً، وفيه قيمة مضافة (نصيحة أو اسم أداة).\n"
                    "الأسلوب: بشري، ودود، وخليجي بيضاء. لا تذكر أنك بوت."
                )
                reply_content, _ = await smart_fetch_content(reply_prompt)
                
                if reply_content:
                    api_v2.create_tweet(text=reply_content, in_reply_to_tweet_id=tweet.id)
                    logger.success(f"💬 تم الرد على: {tweet.id}")
                    await asyncio.sleep(60) # فاصل زمني لتجنب السبام
    except Exception as e:
        logger.error(f"Reply Mission Error: {e}")

# ==========================================
# ⏳ التنفيذ الرئيسي
# ==========================================
async def main():
    logger.info("🚀 تشغيل منظومة أيبكس المتكاملة 2026")
    # 1. نشر الخبر العميق (مرة كل 6 ساعات)
    await apex_post_mission()
    # 2. تفعيل الردود الذكية (اختياري)
    await apex_reply_mission()

if __name__ == "__main__":
    asyncio.run(main())
