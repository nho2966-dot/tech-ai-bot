import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
from loguru import logger
import tweepy
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ⚙️ الإعدادات والمفاتيح
# ==========================================
KEYS = {"GROQ": os.getenv("GROQ_API_KEY")}
X_CRED = {
    "bearer_token": os.getenv("X_BEARER_TOKEN"),
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# القائمة السوداء (الكلمات التي تمنع الرد)
BLACKLIST = ["سياسة", "مخدرات", "عنصرية", "إباحي", "شتم", "سب", "فضيحة"]

try:
    client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)
    BOT_ID = client_v2.get_me().data.id
    logger.success("✅ تم تفعيل الذاكرة والقائمة السوداء!")
except Exception as e:
    logger.error(f"❌ خطأ اتصال: {e}"); exit()

# ==========================================
# 🧠 نظام منع تكرار المحتوى (الذاكرة)
# ==========================================
def is_already_posted(link, filename="posted_links.txt"):
    if not os.path.exists(filename): return False
    with open(filename, "r") as f:
        posted = f.read().splitlines()
    return link in posted

def save_posted_link(link, filename="posted_links.txt"):
    with open(filename, "a") as f:
        f.write(link + "\n")

# ==========================================
# 🛡️ محرك الذكاء الاصطناعي (أيبكس)
# ==========================================
async def ai_guard(prompt, mode="news"):
    # إذا كان المنشن يحتوي كلمة من القائمة السوداء، نلغي الرد فوراً
    if any(word in prompt.lower() for word in BLACKLIST):
        return "SKIP"

    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    prompts = {
        "news": "صغ خبر تقني بلهجة خليجية بيضاء عن الذكاء الاصطناعي وأدواته، بدون كلمات إنجليزية إلا بين أقواس.",
        "reply": "رد بذكاء خليجي تقني وبأدب رصين.",
        "snipe": "اقتبس التغريدة وعلق عليها بذكاء خليجي يوضح الفائدة التقنية."
    }

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": f"أنت 'أيبكس'. {prompts.get(mode)}"}, {"role": "user", "content": prompt}],
            temperature=0.1 # تقليل الحرارة لضمان دقة الخبر وعدم الهلوسة
        )
        return response.choices[0].message.content.strip()
    except: return "SKIP"

# ==========================================
# 🚀 محرك النشر الدوري (مع منع التكرار)
# ==========================================
async def post_daily_news():
    logger.info("📰 فحص الأخبار الجديدة...")
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://aitnews.com/feed/", timeout=10)
            soup = BeautifulSoup(r.content, 'xml')
            items = soup.find_all('item')
            
            for item in items:
                link = item.link.text
                # إذا الخبر تم نشره من قبل، ننتقل للخبر اللي بعده
                if is_already_posted(link):
                    continue
                
                title = item.title.text
                tweet_text = await ai_guard(title, mode="news")
                
                if "SKIP" not in tweet_text:
                    client_v2.create_tweet(text=f"{tweet_text}\n\n🔗 {link}")
                    save_posted_link(link) # حفظ الرابط في الذاكرة
                    logger.success(f"✅ تم نشر خبر جديد وحفظه في الذاكرة: {title}")
                    return # نكتفي بنشر خبر واحد في كل دورة
            
            logger.info("😴 لا يوجد أخبار جديدة لم تُنشر من قبل.")
    except Exception as e:
        logger.error(f"❌ خطأ في محرك النشر: {e}")

# ==========================================
# 🚀 تشغيل المحرك الكامل
# ==========================================
async def run_apex_engine():
    # ترتيب العمليات: رد على المنشن -> قنص -> نشر خبر جديد
    # (تم اختصار الكود هنا للتركيز على الحل، احتفظ بدوال الرد والقنص السابقة وادمجها)
    await post_daily_news()

if __name__ == "__main__":
    asyncio.run(run_apex_engine())
