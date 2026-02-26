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
# 🔐 KEYS & AUTH
# =========================================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
XAI_KEY = os.getenv("XAI_API_KEY")        
QWEN_KEY = os.getenv("QWEN_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

auth = tweepy.OAuth1UserHandler(X_KEY, X_SECRET, X_TOKEN, X_ACCESS_S)
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=X_KEY, consumer_secret=X_SECRET,
    access_token=X_TOKEN, access_token_secret=X_ACCESS_S,
    wait_on_rate_limit=True 
)

# =========================================================
# 🗄 DATABASE
# =========================================================
conn = sqlite3.connect("tech_sovereign_flexible.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS published (hash TEXT PRIMARY KEY, time TEXT)")
conn.commit()

# =========================================================
# ⚙️ CONFIGURABLE PARAMETERS
# =========================================================
daily_videos_count = 1           
video_length_seconds = 45        
tweets_per_thread = 3            

# =========================================================
# 🛡 IMPROVED FILTER
# =========================================================
def content_filter(text):
    if not text: return ""
    banned = [
        "stock","market","investment","funding","revenue","profit","سهم","تداول","عملة","cryptocurrency","بيتكوين", "ناصر", "خبير"
    ]
    for word in banned: 
        text = re.sub(rf"\b{word}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r'^(التغريدة \d+:|تغريدة \d+)\s*', '', text, flags=re.IGNORECASE).strip()
    return text

# =========================================================
# 🧠 SOVEREIGN BRAIN
# =========================================================
class SovereignBrain:
    async def generate(self, prompt, system_msg):
        brains = []
        if GEMINI_KEY: brains.append(("GEMINI", f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Authorization": f"Bearer {GEMINI_KEY}"}, "gemini-2.5-flash"))
        if GROQ_KEY: brains.append(("GROQ", "https://api.groq.com/openai/v1/chat/completions", {"Authorization": f"Bearer {GROQ_KEY}"}, "llama-3.3-70b-versatile"))
        if XAI_KEY: brains.append(("GROK", "https://api.x.ai/v1/chat/completions", {"Authorization": f"Bearer {XAI_KEY}"}, "grok-2-latest"))
        if OPENROUTER_KEY: brains.append(("OPENROUTER", "https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {OPENROUTER_KEY}"}, "google/gemini-2.5-flash"))
        if OPENAI_KEY: brains.append(("OPENAI", "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {OPENAI_KEY}"}, "gpt-4o-mini"))

        for name, url, headers, model in brains:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    r = await client.post(url, headers=headers, json={
                        "model": model,
                        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
                    })
                    r.raise_for_status()
                    return r.json()['choices'][0]['message']['content']
            except Exception as e:
                logger.warning(f"⚠️ Brain {name} failed: {e}")
                continue
        logger.error("❌ فشلت جميع نماذج الذكاء الاصطناعي في الاستجابة!")
        return None

brain = SovereignBrain()

# =========================================================
# 🎥 MULTI-SOURCE RADAR
# =========================================================
TRUSTED_CHANNELS = [
    "https://www.youtube.com/@mkbhd",
    "https://www.youtube.com/@Mrwhosetheboss",
    "https://www.youtube.com/@ProperHonestTech",
    "https://www.youtube.com/@HowToMen",
    "https://www.youtube.com/@MattWolfe",
    "https://www.youtube.com/@TheAIAdvantage",
    "https://www.youtube.com/@ThioJoe",
    "https://www.youtube.com/@zoneoftech",
    "https://www.youtube.com/@TechSpurt",
    "https://www.youtube.com/@AndroidAuthority",
    "https://www.youtube.com/@TheVerge",
    "https://www.youtube.com/@cnet"
]

SEARCH_QUERIES = [
    "ytsearch10: tech tips and tricks",
    "ytsearch10: hidden smartphone features shorts",
    "ytsearch10: secret iphone tricks",
    "ytsearch10: best AI tools tutorial",
    "ytsearch10: android hacks shorts",
    "ytsearch10: cool tech gadgets"
]

def fetch_tech_video():
    logger.info("🔎 البحث عن خبايا تقنية جديدة من القنوات الموثوقة...")
    ydl_opts_channels = {'quiet': True, 'extract_flat': True, 'daterange': yt_dlp.utils.DateRange('now-3days','now')}
    random.shuffle(TRUSTED_CHANNELS)
    
    with yt_dlp.YoutubeDL(ydl_opts_channels) as ydl:
        for channel in TRUSTED_CHANNELS:
            try:
                res = ydl.extract_info(channel, download=False)
                if 'entries' in res and res['entries']:
                    for video in res['entries'][:5]:
                        title = video.get('title') or ""
                        v_url = video.get('url') or (f"https://www.youtube.com/watch?v={video.get('id')}" if video.get('id') else None)
                        
                        if not v_url: continue
                        if any(w in title.lower() for w in ["stock","market","earnings","review","podcast"]): continue
                            
                        v_hash = hashlib.sha256(title.encode()).hexdigest()
                        cursor.execute("SELECT hash FROM published WHERE hash=?", (v_hash,))
                        if cursor.fetchone(): continue 
                            
                        return {"title": title, "url": v_url, "hash": v_hash}
            except Exception:
                continue

    logger.info("⚠️ لم نجد فيديوهات جديدة في القنوات، جاري تفعيل محرك البحث المفتوح الشامل...")
    ydl_opts_search = {'quiet': True, 'extract_flat': True} 
    random.shuffle(SEARCH_QUERIES)
    
    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
        for query in SEARCH_QUERIES:
            try:
                res = ydl.extract_info(query, download=False)
                if 'entries' in res and res['entries']:
                    for video in res['entries']:
                        title = video.get('title') or ""
                        v_url = video.get('url') or (f"https://www.youtube.com/watch?v={video.get('id')}" if video.get('id') else None)
                        
                        if not v_url: continue
                        if any(w in title.lower() for w in ["stock","market","earnings","review","podcast"]): continue
                            
                        v_hash = hashlib.sha256(title.encode()).hexdigest()
                        cursor.execute("SELECT hash FROM published WHERE hash=?", (v_hash,))
                        if cursor.fetchone(): continue 
                            
                        return {"title": title, "url": v_url, "hash": v_hash}
            except Exception as e:
                logger.warning(f"⚠️ فشل البحث في الاستعلام {query}: {e}")
                continue

    return None

def process_video(url):
    logger.info("🎬 تحميل ومعالجة الفيديو...")
    output_raw = "raw_vid.mp4"
    output_final = "tech_vid.mp4"
    
    ydl_opts = {'format':'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', 'outtmpl': output_raw, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    
    cmd = [
        "ffmpeg", "-y", "-i", output_raw, "-t", str(video_length_seconds),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-c:a", "aac", output_final
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_final

# =========================================================
# 🐦 THREAD POSTING (WITH VIDEO)
# =========================================================
async def post_video_thread(title, video_path):
    prompt = f"""اكتب سلسلة من {tweets_per_thread} تغريدات تفصيلية تشرح هذا الموضوع التقني: ({title}).
يجب أن تحتوي السلسلة على قيمة مضافة حقيقية ومعلومات دسمة (استغل مساحة X Premium).

القالب الإلزامي:
التغريدة 1: ادخل في صلب الموضوع مباشرة. اذكر اسم التقنية/الميزة والفائدة الحقيقية التي ستقدمها للمستخدم (بدون مقدمات طويلة).
التغريدة 2: اشرح "كيف تعمل" هذه التقنية بالتفصيل أو اذكر مميزاتها القوية بأمثلة عملية.
التغريدة 3: اذكر "كيفية الاستخدام" أو الخطوات العملية للاستفادة منها، واختم بـ 2 هاشتاجات.

يجب الفصل بين كل تغريدة وأخرى بسطرين فارغين (\\n\\n)."""

    system = "أنت حساب تقني احترافي يقدم محتوى عالي الجودة. لا تستخدم أي أسماء شخصية. لا تكتب مقدمات فارغة أو ثرثرة. قدم معلومة تقنية مركزة، مفصلة، ومفيدة جداً للقارئ بأسلوب خليجي واضح."
    
    raw_content = await brain.generate(prompt, system)
    if not raw_content: return
        
    tweets = [content_filter(t) for t in raw_content.split('\n\n') if len(t.strip()) > 10][:tweets_per_thread]
    if len(tweets) < tweets_per_thread: return
    
    logger.info("🐦 رفع الفيديو والتغريدة الأولى...")
    media = api_v1.media_upload(video_path, media_category='tweet_video', chunked=True)
    
    for _ in range(15):
        try:
            status = api_v1.get_media_upload_status(media.media_id)
            if status.processing_info.get("state") == "succeeded": break
        except: pass
        time.sleep(5)
    
    try:
        first_tweet = client_v2.create_tweet(text=tweets[0], media_ids=[media.media_id])
        last_id = first_tweet.data['id']
        
        for i in range(1, len(tweets)):
            # أنسنة: فاصل زمني عشوائي بين 10 و 25 ثانية ليوحي بأن هناك من يكتب
            delay = random.randint(10, 25)
            logger.info(f"⏳ (أنسنة) جاري الانتظار لمدة {delay} ثانية قبل نشر التغريدة التالية...")
            await asyncio.sleep(delay)
            
            reply = client_v2.create_tweet(text=tweets[i], in_reply_to_tweet_id=last_id)
            last_id = reply.data['id']
            
        logger.success("✅ تم نشر السلسلة التقنية (مع الفيديو) بنجاح!")
    except Exception as e:
        logger.error(f"❌ فشل النشر على منصة X. السبب: {e}")

# =========================================================
# 📝 TEXT ONLY FALLBACK
# =========================================================
async def post_text_only_thread():
    logger.info("📝 تفعيل الخطة البديلة: جاري إنشاء محتوى نصي...")
    
    tech_topics = [
        "ميزة مخفية في الآيفون لحماية الخصوصية من التطبيقات التي تتجسس على الحافظة (Clipboard).",
        "طريقة استخدام الذكاء الاصطناعي لتلخيص ملفات PDF الطويلة جداً في ثوانٍ.",
        "كيفية تفعيل ميزة عزل الصوت المحيطي في المكالمات المزدحمة للآيفون والأندرويد.",
        "تطبيق مخفي أو ميزة غير معروفة لتحسين أداء بطارية الهاتف وإيقاف استنزاف الخلفية."
    ]
    topic = random.choice(tech_topics)

    prompt = f"""اكتب سلسلة من {tweets_per_thread} تغريدات تفصيلية تشرح هذا الموضوع: ({topic}).
يجب أن تقدم السلسلة قيمة مضافة حقيقية ومعلومات دقيقة (استغل مساحة X Premium).

القالب الإلزامي:
التغريدة 1: ادخل في صلب الموضوع مباشرة. اشرح الفائدة الحقيقية ولماذا يحتاج المستخدم هذه الميزة (تجنب المقدمات الفارغة).
التغريدة 2: اشرح بتعمق كيف تعمل الميزة، وأين توجد بالضبط في النظام أو التطبيق.
التغريدة 3: اكتب "الخطوات العملية" 1، 2، 3 بشكل واضح جداً ليتمكن المستخدم من تطبيقها فوراً، واختم بهاشتاجين.

يجب الفصل بين كل تغريدة وأخرى بسطرين فارغين (\\n\\n)."""

    system = "أنت حساب تقني احترافي يقدم محتوى عالي الجودة. لا تستخدم أي أسماء شخصية. لا تكتب مقدمات فارغة. قدم معلومة تقنية مركزة، مفصلة، ومفيدة جداً للقارئ بأسلوب خليجي واضح ومباشر."
    
    raw_content = await brain.generate(prompt, system)
    if not raw_content: return
        
    tweets = [content_filter(t) for t in raw_content.split('\n\n') if len(t.strip()) > 10][:tweets_per_thread]
    if len(tweets) < tweets_per_thread: return
        
    logger.info("🐦 جاري نشر السلسلة النصية... إليك المحتوى الذي سيتم نشره:")
    for idx, t in enumerate(tweets):
        logger.info(f"التغريدة {idx+1}:\n{t}\n---")
        
    try:
        first_tweet = client_v2.create_tweet(text=tweets[0])
        last_id = first_tweet.data['id']
        
        for i in range(1, len(tweets)):
            # أنسنة: فاصل زمني عشوائي بين 10 و 25 ثانية ليوحي بأن هناك من يكتب
            delay = random.randint(10, 25)
            logger.info(f"⏳ (أنسنة) جاري الانتظار لمدة {delay} ثانية قبل نشر التغريدة التالية...")
            await asyncio.sleep(delay)
            
            reply = client_v2.create_tweet(text=tweets[i], in_reply_to_tweet_id=last_id)
            last_id = reply.data['id']
            
        logger.success("✅ تم نشر السلسلة النصية البديلة بنجاح!")
    except Exception as e:
        logger.error(f"❌ فشل النشر على منصة X: {e}")

# =========================================================
# 🚀 EXECUTION FLOW
# =========================================================
async def run_daily_task():
    for _ in range(daily_videos_count):
        video_data = fetch_tech_video()
        
        if not video_data: 
            logger.warning("⚠️ لا توجد فيديوهات جديدة لم تُنشر اليوم.")
            await post_text_only_thread()
            return

        v_hash = video_data['hash']

        try:
            final_vid = process_video(video_data['url'])
            await post_video_thread(video_data['title'], final_vid)
            
            cursor.execute("INSERT INTO published VALUES (?,?)", (v_hash, datetime.utcnow().isoformat()))
            conn.commit()
            
            for f in ["raw_vid.mp4", "tech_vid.mp4"]:
                if os.path.exists(f): os.remove(f)
                
        except Exception as e:
            logger.error(f"❌ حدث خطأ أثناء معالجة أو رفع الفيديو: {e}")
            await post_text_only_thread()

if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل السكربت من GitHub Actions...")
    asyncio.run(run_daily_task())
    logger.info("🏁 تمت المهمة وسيتم إغلاق السكربت للحفاظ على الموارد.")
