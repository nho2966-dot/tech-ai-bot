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
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# إعداد v1.1 لرفع الميديا (الصور)
auth_v1 = tweepy.OAuth1UserHandler(
    X_CRED["consumer_key"], X_CRED["consumer_secret"],
    X_CRED["access_token"], X_CRED["access_token_secret"]
)
api_v1 = tweepy.API(auth_v1)

GIANTS_TO_SNIPE = ["44196397", "76837396"] 
TIME_WINDOW_MINUTES = 120

MASTER_RSS_FEEDS = [
    "https://aitnews.com/feed/",                 
    "https://www.tech-wd.com/wd/feed/",          
    "https://www.unlimit-tech.com/feed/",        
    "https://techcrunch.com/category/artificial-intelligence/feed/", 
    "https://www.theverge.com/rss/index.xml",    
    "https://www.wired.com/feed/category/gear/latest/rss", 
    "https://9to5mac.com/feed/"                
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
IMG_TEMP_FILE = "temp_news_img.jpg"

# ==========================================
# 📡 محرك الرادار (جمع البيانات + الصور)
# ==========================================
async def fetch_article_text(url, http_client):
    try:
        response = await http_client.get(url, headers=HEADERS, follow_redirects=True, timeout=15.0)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            paragraphs = soup.find_all('p')
            return " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text())>20])[:1500]
    except: return ""

async def fetch_latest_tech_news_with_image():
    news_data = {"text": "", "img_url": None}
    selected_feeds = random.sample(MASTER_RSS_FEEDS, min(3, len(MASTER_RSS_FEEDS)))
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        for feed in selected_feeds:
            try:
                response = await client.get(feed, headers=HEADERS)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "xml")
                    for item in soup.find_all('item', limit=2):
                        title = item.title.text if item.title else ""
                        link = item.link.text if item.link else ""
                        img_url = None
                        
                        media = item.find('media:content')
                        if media: img_url = media.get('url')
                        elif item.description:
                            d_soup = BeautifulSoup(item.description.text, "html.parser")
                            img = d_soup.find('img')
                            if img: img_url = img.get('src')
                        
                        article_text = await fetch_article_text(link, client)
                        if article_text:
                            news_data["text"] += f"العنوان: {title}\nالرابط: {link}\nالتفاصيل: {article_text}\n---\n"
                            if img_url and not news_data["img_url"]: news_data["img_url"] = img_url
            except: continue
    return news_data

# ==========================================
# 🧠 عقل "أيبكس" (التعديل الحاسم للصياغة)
# ==========================================
async def create_news_tweet(news_context, recent_texts, has_image=False):
    img_hint = " (ملاحظة: سنرفق صورة، اجعل النص متناغماً معها)" if has_image else ""
    sys_msg = f"""أنت "أيبكس"، محلل تقني محترف. 
    مهمتك: اختر خبراً واحداً فقط وصُغه في قالب واحد من القوالب التالية (دون ذكر اسم القالب):

    1. [تغريدة تحليلية]: (خطاف صادم + زبدة الخبر + رابط المصدر).
    2. [استطلاع رأي - POLL]: اكتب نصاً يثير الفضول ثم ألحقه مباشرة بـ [POLL: خيار1, خيار2].
       ⚠️ (قيد صارم: كل خيار يجب أن يكون كلمة أو كلمتين فقط، بحد أقصى 20 حرفاً).
    3. [ثريد - Thread]: فكك الخبر لـ 3 تغريدات مرقمة (1/3، 2/3، 3/3).

    ❌ ممنوع تماماً:
    - لا تسرد الخيارات الثلاثة للمتابع.
    - لا تقل "لديك خيارات" أو "أخبار جديدة".
    - ابدأ النص مباشرة وبقوة.
    - الرابط دائماً في نهاية التغريدة الأولى.
    {img_hint}
    """
    
    prompt = f"الأخبار الحالية:\n{news_context}\nالمواضيع السابقة: [{recent_texts}]\nصغ المحتوى الآن:"
    return await generate_ai_content(prompt, sys_msg)

async def generate_ai_content(prompt, system_msg):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"])
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system_msg},{"role":"user","content":prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()
    except: return None

# ==========================================
# 📤 محرك النشر التفاعلي (Interactive Polls)
# ==========================================
async def publish_smart_content(client_v2, ai_output, media_id=None):
    try:
        # الثريدات
        if "1/3" in ai_output:
            tweets = [t.strip() for t in ai_output.split("\n\n") if len(t.strip()) > 5][:3]
            last_id = None
            for i, text in enumerate(tweets):
                res = client_v2.create_tweet(text=text[:280], media_ids=[media_id] if media_id and i==0 else None, in_reply_to_tweet_id=last_id)
                last_id = res.data['id']
            logger.success("🧵 تم نشر ثريد.")

        # الاستطلاعات التفاعلية (أزرار قابلة للنقر)
        elif "[POLL:" in ai_output:
            parts = ai_output.split("[POLL:")
            main_text = parts[0].strip()
            raw_opts = parts[1].replace("]", "").split(",")
            # قص آلي لضمان عمل الأزرار (تويتر يرفض أكثر من 25 حرف للخيار)
            safe_opts = [o.strip()[:25] for o in raw_opts if o.strip()][:4]
            
            if len(safe_opts) >= 2:
                client_v2.create_tweet(
                    text=main_text[:280], 
                    poll_options=safe_opts, 
                    poll_duration_minutes=1440
                )
                logger.success(f"📊 تم نشر استطلاع بأزرار تفاعلية: {safe_opts}")
            else:
                client_v2.create_tweet(text=main_text[:280], media_ids=[media_id] if media_id else None)

        # التغريدة العادية
        else:
            client_v2.create_tweet(text=ai_output[:280], media_ids=[media_id] if media_id else None)
            logger.success("📝 تم نشر تغريدة.")
            
    except Exception as e: logger.error(f"❌ خطأ نشر: {e}")

# ==========================================
# 🏁 الدورة الرئيسية
# ==========================================
async def bot_cycle():
    client_v2 = tweepy.Client(**X_CRED)
    try: bot_id = client_v2.get_me().data.id
    except: return

    recent_txt = ""
    try:
        recent = client_v2.get_users_tweets(id=bot_id, max_results=10)
        if recent.data: recent_txt = " | ".join([t.text for t in recent.data])
    except: pass

    news_data = await fetch_latest_tech_news_with_image()
    if news_data["text"]:
        ai_msg = await create_news_tweet(news_data["text"], recent_txt, bool(news_data["img_url"]))
        
        if ai_msg and "SKIP" not in ai_msg.upper():
            mid = None
            if news_data["img_url"]:
                try:
                    async with httpx.AsyncClient() as c:
                        r = await c.get(news_data["img_url"])
                        with open(IMG_TEMP_FILE, 'wb') as f: f.write(r.content)
                        mid = api_v1.media_upload(filename=IMG_TEMP_FILE).media_id
                        os.remove(IMG_TEMP_FILE)
                except: pass
            await publish_smart_content(client_v2, ai_msg, mid)

if __name__ == "__main__":
    asyncio.run(bot_cycle())
