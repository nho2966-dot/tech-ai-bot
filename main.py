import os
import asyncio
import httpx
import random
import tweepy
from datetime import datetime

# --- إعدادات التوثيق ---
# تليجرام
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# إكس (X)
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
# جمناي
GEMINI_KEY = os.getenv("GEMINI_KEY")

# --- محرك الشخصية ---
APEX_RULES = "أنت أيبكس، خبير تقني خليجي. تخصصك Artificial Intelligence and its latest tools. لهجتك خليجية بيضاء."

async def generate_content(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json={"contents":[{"parts":[{"text": f"{APEX_RULES} {prompt}"}]}]}, timeout=40)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

# --- وظيفة النشر في X (ثريد) ---
def publish_to_x(thread_list):
    try:
        auth = tweepy.Client(
            consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET
        )
        previous_tweet_id = None
        for i, tweet in enumerate(thread_list):
            if i == 0:
                response = auth.create_tweet(text=tweet)
            else:
                response = auth.create_tweet(text=tweet, in_reply_to_tweet_id=previous_tweet_id)
            previous_tweet_id = response.data['id']
        print("✅ تم النشر في X بنجاح")
    except Exception as e:
        print(f"❌ خطأ في X: {e}")

# --- وظيفة النشر في تليجرام ---
async def publish_to_tg(content, photo_url, poll_q, poll_options):
    async with httpx.AsyncClient() as client:
        base_url = f"https://api.telegram.org/bot{TG_TOKEN}"
        # 1. إرسال الثريد كنص واحد منسق
        await client.post(f"{base_url}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": content, "parse_mode": "HTML"})
        # 2. إرسال الصورة
        await client.post(f"{base_url}/sendPhoto", json={"chat_id": TG_CHAT_ID, "photo": photo_url, "caption": "📸 رؤية أيبكس التقنية"})
        # 3. إرسال الاستطلاع
        await client.post(f"{base_url}/sendPoll", json={
            "chat_id": TG_CHAT_ID, "question": poll_q, "options": poll_options, "is_anonymous": False
        })

# --- المحرك الرئيسي ---
async def run_apex_system():
    topic = "أحدث أدوات الـ AI الشخصية في 2026"
    
    # توليد المحتوى
    thread_raw = await generate_content(f"اكتب ثريد من 3 تغريدات عن {topic}. اجعلها مشوقة مع رابط مصدر تخيلي احترافي.")
    thread_list = thread_raw.split("\n\n")[:3]
    
    full_tg_content = f"🧵 <b>ثريد أيبكس التقني</b>\n\n" + "\n\n".join(thread_list)
    photo_url = f"https://source.unsplash.com/featured/?technology,ai"
    
    # النشر
    print("🚀 جاري النشر في المنصات...")
    # 1. تليجرام
    await publish_to_tg(full_tg_content, photo_url, f"وش رايكم في {topic}؟", ["رهيب 🚀", "عادي 🧐"])
    # 2. إكس
    publish_to_x(thread_list)

if __name__ == "__main__":
    asyncio.run(run_apex_system())
