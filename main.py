import os
import asyncio
import httpx
import tweepy
import sqlite3
import hashlib
import random
import re
import subprocess
import yt_dlp
import time
from datetime import datetime
from loguru import logger

# =========================================================
# 🔐 KEYS & AUTH (إدارة المفاتيح والرموز)
# =========================================================
GEMINI_KEY = os.getenv("GEMINI_KEY")
X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# تليجرام للإشعارات (اختياري)
TG_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

auth = tweepy.OAuth1UserHandler(X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S)
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=X_KEY, consumer_secret=X_SECRET,
    access_token=X_TOKEN, access_token_secret=X_ACCESS_S,
    wait_on_rate_limit=True 
)

# =========================================================
# 🗄 DATABASE (منع التكرار والردود المتكررة)
# =========================================================
conn = sqlite3.connect("nasser_scoops_final.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS published (hash TEXT PRIMARY KEY, topic TEXT, time TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS interactions (tweet_id TEXT, user_id TEXT, PRIMARY KEY(tweet_id, user_id))")
conn.commit()

# =========================================================
# 🛡️ THE NASSER FILTER (الفلتر السيادي)
# =========================================================
def nasser_filter(text):
    if not text: return ""
    # الالتزام بالمصطلح المتفق عليه
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    
    # منع الكلمات المالية والرموز الغريبة (السماح بالعربي، الإنجليزي، الأرقام، والإيموجي فقط)
    banned = ["stock","market","investment","سهم","تداول","عملة","crypto"]
    for word in banned:
        text = re.sub(rf"\b{word}\b", "", text, flags=re.IGNORECASE)
    
    # إزالة مقدمات الذكاء الاصطناعي التقليدية
    text = re.sub(r'^(التغريدة \d+:|تغريدة \d+)\s*', '', text, flags=re.IGNORECASE).strip()
    return text

# =========================================================
# 🧠 SCOOP BRAIN (توليد الخبايا والتسريبات)
# =========================================================
class SovereignBrain:
    async def generate(self, prompt, system_msg):
        # التركيز على Gemini لقوته في اللهجة الخليجية وعدم الهلوسة
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {"Authorization": f"Bearer {GEMINI_KEY}"}
        
        # تزويد الـ AI بآخر 5 موضوعات لمنع التكرار بصيغ مختلفة
        cursor.execute("SELECT topic FROM published ORDER BY time DESC LIMIT 5")
        past_topics = [row[0] for row in cursor.fetchall()]
        
        full_system = f"{system_msg} | المواضيع السابقة (يمنع تكرارها): {past_topics} | اللهجة: خليجية بيضاء | التركيز: خبايا وتسريبات فقط."
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {
                    "model": "gemini-2.5-flash",
                    "messages": [{"role": "system", "content": full_system}, {"role": "user", "content": prompt}]
                }
                r = await client.post(url, headers=headers, json=payload)
                return nasser_filter(r.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"⚠️ Brain Error: {e}")
            return None

brain = SovereignBrain()

# =========================================================
# 🎥 LEAK RADAR (البحث عن الجديد)
# =========================================================
SEARCH_QUERIES = [
    "ytsearch5: AI hidden features 2026",
    "ytsearch5: ChatGPT secret hacks shorts",
    "ytsearch5: new AI tools leaks",
    "ytsearch5: hidden productivity AI tricks"
]

def fetch_leak_video():
    ydl_opts = {'quiet': True, 'extract_flat': True}
    query = random.choice(SEARCH_QUERIES)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            res = ydl.extract_info(query, download=False)
            for video in res['entries']:
                v_hash = hashlib.md5(video['title'].encode()).hexdigest()
                cursor.execute("SELECT 1 FROM published WHERE hash=?", (v_hash,))
                if not cursor.fetchone():
                    return {"title": video['title'], "url": f"https://www.youtube.com/watch?v={video['id']}", "hash": v_hash}
        except: return None
    return None

# =========================================================
# 🐦 نشر "الخبايا" (Thread Posting)
# =========================================================
async def post_scoop_thread():
    video_data = fetch_leak_video()
    
    # اختيار "زاوية" المحتوى لضمان التنوع
    angle = random.choice(["تسريب حصري", "خبايا مخفية", "قنبلة تقنية", "ميزة سرية"])
    
    prompt = f"اكتب سلسلة من 3 تغريدات دسمة بأسلوب '{angle}' عن: {video_data['title'] if video_data else 'أحدث أداة AI للأفراد'}. ركز على المعلومات اللي ما يعرفها الجميع."
    system = "أنت ناصر، المصدر الأول للخبايا التقنية. أسلوبك مثير ومهني، تظهر بمظهر المطلع على ما وراء الكواليس. استخدم لهجة خليجية مرموقة."

    raw_content = await brain.generate(prompt, system)
    if not raw_content: return

    tweets = [t.strip() for t in raw_content.split('\n\n') if len(t) > 10]
    
    try:
        # إذا وجدنا فيديو، نرفعه مع أول تغريدة
        media_ids = []
        if video_data:
            logger.info(f"🎬 معالجة فيديو الخبايا: {video_data['title']}")
            # (هنا تتم عملية التحميل والقص بـ ffmpeg كما في كودك السابق)
            # تم اختصارها هنا للتركيز على منطق النشر
            
        first_tweet = client_v2.create_tweet(text=tweets[0])
        last_id = first_tweet.data['id']
        
        for i in range(1, len(tweets)):
            await asyncio.sleep(random.randint(15, 30)) # أنسنة التوقيت
            reply = client_v2.create_tweet(text=tweets[i], in_reply_to_tweet_id=last_id)
            last_id = reply.data['id']
            
        if video_data:
            cursor.execute("INSERT INTO published VALUES (?,?,?)", (video_data['hash'], angle, datetime.now().isoformat()))
            conn.commit()
        logger.success(f"✅ تم نشر {angle} بنجاح!")
    except Exception as e:
        logger.error(f"❌ فشل نشر الخبايا: {e}")

# =========================================================
# 💬 الردود الذكية (Reply Later)
# =========================================================
async def smart_reply_cycle():
    me = client_v2.get_me()
    my_id = str(me.data.id)
    
    mentions = client_v2.get_users_mentions(id=my_id, max_results=5, expansions=['author_id'])
    if not mentions.data: return

    for tweet in mentions.data:
        author_id = str(tweet.author_id)
        if author_id == my_id: continue # منع الرد على النفس
        
        cursor.execute("SELECT 1 FROM interactions WHERE tweet_id=? AND user_id=?", (tweet.id, author_id))
        if cursor.fetchone(): continue # منع الرد المكرر لنفس الشخص

        prompt = f"رد باختصار وذكاء بلهجة خليجية على هذا المتابع بخصوص خفايا التقنية: {tweet.text}"
        reply = await brain.generate(prompt, "أنت ناصر، ترد على جمهورك بذكاء وتواضع خبير.")
        
        if reply:
            client_v2.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
            cursor.execute("INSERT INTO interactions VALUES (?, ?)", (tweet.id, author_id))
            conn.commit()
            logger.info(f"✅ تم الرد ذكياً على {author_id}")

# =========================================================
# 🚀 السيرفر الرئيسي
# =========================================================
async def main():
    logger.info("🌟 بدء تشغيل بوت الخبايا والتسريبات التقنية...")
    while True:
        # 1. دورة النشر (خبايا جديدة)
        await post_scoop_thread()
        
        # 2. انتظار تفاعل الناس ثم الرد
        await asyncio.sleep(600)
        await smart_reply_cycle()
        
        # 3. قيلولة تقنية طويلة (للحفاظ على جودة الحساب و Content Freshness)
        wait_time = random.randint(7200, 14400) # 2-4 ساعات
        logger.info(f"💤 قيلولة لمدة {wait_time/3600:.1f} ساعة...")
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(main())
