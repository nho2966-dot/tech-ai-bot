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
# ⚙️ الإعدادات المعتمدة من الـ Secrets الخاصة بك
# ==========================================
X_CRED = {
    "bearer_token": os.getenv("X_BEARER_TOKEN"),
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# المراجع الموثوقة (مثل Google AI)
OFFICIAL_REFS = ["GoogleAI", "OpenAI", "DeepMind", "MetaAI", "AnthropicAI"]
RSS_FEEDS = ["https://aitnews.com/feed/", "https://www.tech-wd.com/wd/feed/"]

try:
    # استخدام Bearer Token للعمليات الحساسة لضمان تخطي خطأ 401
    client_v2 = tweepy.Client(
        bearer_token=X_CRED["bearer_token"],
        consumer_key=X_CRED["consumer_key"],
        consumer_secret=X_CRED["consumer_secret"],
        access_token=X_CRED["access_token"],
        access_token_secret=X_CRED["access_token_secret"],
        wait_on_rate_limit=True
    )
    BOT_ID = client_v2.get_me().data.id
    logger.success("✅ تم ربط المفاتيح بنجاح يا ناصر!")
except Exception as e:
    logger.error(f"❌ تأكد من صحة مفاتيح X في الـ Secrets: {e}"); exit()

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (أيبكس)
# ==========================================
async def ai_guard(prompt, mode="news"):
    # نستخدم GROQ للسرعة والكفاءة كما هو موجود في قائمتك
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
    
    sys_prompt = """أنت 'أيبكس'. خبير في الذكاء الاصطناعي وأحدث أدواته.
    - اللهجة: خليجية بيضاء (مزيج راقي).
    - القيود: ممنوع ذكر 'الثورة الصناعية'، استبدلها بـ 'الذكاء الاصطناعي وأحدث أدواته'.
    - المحتوى: ركز على الفائدة المباشرة للأفراد."""

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
# 🎯 محرك القنص ومنع التكرار
# ==========================================
async def run_apex_engine():
    # 1. القنص من المراجع (اقتباس تغريدة تقنية)
    target = random.choice(OFFICIAL_REFS)
    try:
        user = client_v2.get_user(username=target)
        tweets = client_v2.get_users_tweets(id=user.data.id, max_results=5)
        if tweets.data:
            comment = await ai_guard(tweets.data[0].text, mode="snipe")
            if "SKIP" not in comment:
                await asyncio.sleep(random.randint(60, 180)) # فاصل بشري
                client_v2.create_tweet(text=comment, quote_tweet_id=tweets.data[0].id)
                logger.success(f"🚀 تم قنص تغريدة {target}")
    except Exception as e: logger.error(f"⚠️ فشل القنص: {e}")

    # 2. نشر خبر RSS (مع فحص التكرار)
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(random.choice(RSS_FEEDS), timeout=10)
            soup = BeautifulSoup(r.content, 'xml')
            items = soup.find_all('item')
            
            # فحص آخر تغريداتنا لمنع تكرار الخبر
            my_history = client_v2.get_users_tweets(id=BOT_ID, max_results=15)
            history_text = [t.text for t in my_history.data] if my_history.data else []

            for item in items:
                link = item.link.text
                if any(link in h for h in history_text): continue
                
                txt = await ai_guard(item.title.text, mode="news")
                if "SKIP" not in txt:
                    client_v2.create_tweet(text=f"{txt}\n\n🔗 {link}")
                    logger.success("✅ تم نشر خبر جديد وحصري")
                    break 
    except Exception as e: logger.error(f"⚠️ خطأ النشر: {e}")

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
