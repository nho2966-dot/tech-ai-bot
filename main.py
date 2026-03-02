import os
import asyncio
import httpx
import tweepy
import sqlite3
import hashlib
import random
import re
import difflib
import subprocess
from datetime import datetime
from loguru import logger

# --- 🔐 الإعدادات والمفاتيح ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
X_CREDS = {
    "key": os.getenv("X_API_KEY"),
    "secret": os.getenv("X_API_SECRET"),
    "token": os.getenv("X_ACCESS_TOKEN"),
    "access_s": os.getenv("X_ACCESS_SECRET"),
    "bearer": os.getenv("X_BEARER_TOKEN")
}

# إعداد Tweepy (V1 للرفع و V2 للنشر والردود)
auth = tweepy.OAuth1UserHandler(X_CREDS["key"], X_CREDS["secret"], X_CREDS["token"], X_CREDS["access_s"])
api_v1 = tweepy.API(auth)
client_v2 = tweepy.Client(
    bearer_token=X_CREDS["bearer"],
    consumer_key=X_CREDS["key"], consumer_secret=X_CREDS["secret"],
    access_token=X_CREDS["token"], access_token_secret=X_CREDS["access_s"],
    wait_on_rate_limit=True
)

# --- 🗄️ قاعدة البيانات (حفظ البصمات والأفكار) ---
conn = sqlite3.connect("nasser_sovereign_v4.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS archive (hash TEXT PRIMARY KEY, idea TEXT, date TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS replies (tweet_id TEXT PRIMARY KEY, date TEXT)")
conn.commit()

# --- 🛡️ فلاتر ناصر ومنع التكرار ---
def nasser_filter(text):
    if not text: return ""
    text = text.replace("الثورة الصناعية الرابعة", "الذكاء الاصطناعي وأحدث أدواته")
    text = re.sub(r'\b(ناصر|خبير|بوت|آلي)\b', '', text)
    return text.strip()

def is_intellectually_duplicated(new_idea, threshold=0.45):
    cursor.execute("SELECT idea FROM archive")
    past_ideas = [row[0] for row in cursor.fetchall()]
    for old_idea in past_ideas:
        if difflib.SequenceMatcher(None, new_idea, old_idea).ratio() > threshold:
            return True
    return False

# --- 🧠 محرك التوليد (Gemini) ---
async def ask_gemini(prompt, system_msg):
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers = {"Authorization": f"Bearer {GEMINI_KEY}"}
    payload = {
        "model": "gemini-2.0-flash",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, headers=headers, json=payload)
            return nasser_filter(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        logger.error(f"❌ خطأ AI: {e}")
        return None

# --- 📡 رادار الفيديو (خليجي + عالمي) ---
def download_tech_video():
    sources = [
        "https://www.youtube.com/@Omardizer/videos",
        "https://www.youtube.com/@FaisalAlsaif/videos",
        "https://www.youtube.com/@IbrahimAlsuwaid/videos",
        "https://www.youtube.com/@MKBHD/videos",
        "https://www.youtube.com/@theverge/videos"
    ]
    target = random.choice(sources)
    filename = f"vid_{random.randint(10,99)}.mp4"
    logger.info(f"🔎 الرادار يستهدف: {target}")
    
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings", "--format", "b[ext=mp4]",
        "--max-filesize", "15M", "--playlist-items", "1",
        "--download-sections", "*0-35", "-o", filename, target
    ]
    try:
        subprocess.run(cmd, check=True, timeout=100)
        return filename if os.path.exists(filename) else None
    except: return None

# --- 🐦 مهمة النشر التلقائي (فيديو + نص) ---
async def post_scoop():
    video_file = download_tech_video()
    media_id = None
    if video_file:
        try:
            media = api_v1.media_upload(filename=video_file, media_category='tweet_video')
            media_id = media.media_id
        except Exception as e: logger.error(f"❌ فشل رفع الميديا: {e}")

    # توليد فكرة فريدة
    system = "أنت خبير تقني خليجي مطلع على خبايا الذكاء الاصطناعي للأفراد. أسلوبك حماسي ومفيد."
    prompt = "اكتب تغريدة مشوقة عن أداة ذكاء اصطناعي جديدة للأفراد (بدون هاشتاقات زايدة)."
    content = await ask_gemini(prompt, system)
    
    # استخراج "بصمة الفكرة" لمنع التكرار المعنوي
    core_idea = await ask_gemini(f"لخص الفكرة في 3 كلمات: {content}", "محلل محتوى")

    if content and not is_intellectually_duplicated(core_idea):
        try:
            if media_id:
                client_v2.create_tweet(text=content, media_ids=[media_id])
            else:
                client_v2.create_tweet(text=content) # نشر نصي كخطة بديلة
            
            cursor.execute("INSERT INTO archive VALUES (?,?,?)", 
                           (hashlib.md5(content.encode()).hexdigest(), core_idea, datetime.now().isoformat()))
            conn.commit()
            logger.success(f"✅ تم النشر: {core_idea}")
        except Exception as e: logger.error(f"❌ فشل النشر النهائي (تأكد من صلاحيات Write): {e}")
    
    if video_file and os.path.exists(video_file): os.remove(video_file)

# --- 💬 مهمة الردود الذكية المأنسنة ---
async def smart_replies():
    logger.info("💬 فحص التعليقات للرد عليها...")
    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(id=me.id, max_results=5).data
        if not mentions: return

        for tweet in mentions:
            cursor.execute("SELECT 1 FROM replies WHERE tweet_id=?", (str(tweet.id),))
            if cursor.fetchone(): continue

            reply_text = await ask_gemini(f"رد بلهجة خليجية ذكية على: {tweet.text}", "تقني خليجي لبق")
            if reply_text:
                # أنسنة: انتظار بين 1-3 دقائق قبل الرد
                await asyncio.sleep(random.randint(60, 180))
                client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                cursor.execute("INSERT INTO replies VALUES (?,?)", (str(tweet.id), datetime.now().isoformat()))
                conn.commit()
                logger.info(f"✅ تم الرد على {tweet.id}")
    except Exception as e: logger.error(f"❌ خطأ في الردود: {e}")

# --- 🚀 التشغيل ---
async def main():
    await post_scoop()
    await smart_replies()

if __name__ == "__main__":
    asyncio.run(main())
