import os
import asyncio
import httpx
import random
import tweepy

# --- جلب المفاتيح من الصورة (Secrets) ---
GEMINI_KEY = os.getenv("GEMINI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

X_KEY = os.getenv("X_API_KEY")
X_SECRET = os.getenv("X_API_SECRET")
X_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_S = os.getenv("X_ACCESS_SECRET")

# --- محرك توليد المحتوى ---
async def generate_apex_content():
    prompt = """
    أنت أيبكس، خبير تقني خليجي. اكتب ثريد تقني من 3 أجزاء عن 'أدوات AI لزيادة إنتاجية الأفراد في 2026'.
    استخدم لهجة خليجية بيضاء، واجعل كل جزء مفصل. أضف رابط مصدر تخيلي (مثلاً: tech-apex.com).
    فصل بين كل تغريدة بكلمة [SPLIT].
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json={"contents":[{"parts":[{"text":prompt}]}]})
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text.split("[SPLIT]")

# --- النشر في X (ثريد مترابط) ---
def post_to_x(thread_parts):
    try:
        # توثيق V2 للنشر
        client_x = tweepy.Client(
            consumer_key=X_KEY, consumer_secret=X_SECRET,
            access_token=X_TOKEN, access_token_secret=X_ACCESS_S
        )
        
        last_id = None
        for part in thread_parts:
            text = part.strip()[:280] # التأكد من طول التغريدة
            if not last_id:
                response = client_x.create_tweet(text=text)
            else:
                response = client_x.create_tweet(text=text, in_reply_to_tweet_id=last_id)
            last_id = response.data['id']
        print("✅ تم نشر الثريد في X")
    except Exception as e:
        print(f"❌ خطأ X: {e}")

# --- النشر في تليجرام ---
async def post_to_tg(thread_parts):
    full_text = "🧵 <b>ثريد أيبكس التقني</b>\n\n" + "\n\n".join([p.strip() for p in thread_parts])
    base_url = f"https://api.telegram.org/bot{TG_TOKEN}"
    
    async with httpx.AsyncClient() as client:
        # 1. إرسال النص
        await client.post(f"{base_url}/sendMessage", json={
            "chat_id": TG_CHAT_ID, "text": full_text, "parse_mode": "HTML"
        })
        # 2. إرسال الصورة (تستخدم صورة تقنية متغيرة)
        img_url = "https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=1000&auto=format&fit=crop"
        await client.post(f"{base_url}/sendPhoto", json={
            "chat_id": TG_CHAT_ID, "photo": img_url, "caption": "📸 رؤية أيبكس لعام 2026"
        })
        # 3. إرسال استطلاع رأي
        await client.post(f"{base_url}/sendPoll", json={
            "chat_id": TG_CHAT_ID,
            "question": "هل تستخدم هذه الأدوات في عملك؟",
            "options": ["نعم، بشكل يومي 🚀", "قريباً ببدأ ⏳", "أفضل الطريقة التقليدية 🧐"],
            "is_anonymous": False
        })
        print("✅ تم النشر في تليجرام")

# --- التشغيل ---
async def main():
    print("🚀 بدء تشغيل محرك أيبكس...")
    content = await generate_apex_content()
    if content:
        # تنفيذ النشر
        post_to_x(content)
        await post_to_tg(content)

if __name__ == "__main__":
    asyncio.run(main())
