import os
import asyncio
import httpx
import tweepy
import sqlite3
from datetime import datetime, timedelta, timezone
from loguru import logger

# --- الإعدادات ---
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

client_v2 = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# --- 🧠 معايير الجودة ---
def is_low_quality(text):
    if not text or len(text) < 45: return True
    # تجنب الكلمات المكررة بشكل آلي
    if text.count('؟') > 4 or text.count('!') > 4: return True 
    return False

def summarize_for_memory(text):
    return text[:80].replace("\n", " ")

# --- 💬 المحرك المطور ---
async def process_mentions():
    logger.info("🚀 تشغيل النظام الاحترافي V2.1 - استقرار كامل")

    # استخدام context manager لضمان إغلاق الداتابيز
    with sqlite3.connect("memory.db", check_same_thread=False) as db:
        db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                user_id TEXT PRIMARY KEY,
                last_topic TEXT,
                interaction_count INTEGER DEFAULT 1
            )
        """)

        try:
            me = client_v2.get_me().data
            mentions_res = client_v2.get_users_mentions(
                id=me.id,
                tweet_fields=['created_at', 'referenced_tweets', 'author_id'],
                max_results=20 # تقليل العدد لزيادة التركيز والجودة
            )
            
            mentions = mentions_res.data
            if not mentions:
                logger.info("⚡ لا توجد منشنات جديدة.")
                return

            time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

            for t in mentions:
                if t.created_at < time_threshold: continue
                if db.execute("SELECT 1 FROM seen WHERE id=?", (str(t.id),)).fetchone(): continue

                # --- جلب سياق الذاكرة ---
                row = db.execute("SELECT last_topic, interaction_count FROM user_memory WHERE user_id=?", (str(t.author_id),)).fetchone()
                user_context = f"هذا المتابع تفاعل معك {row[1]} مرات، آخرها عن: {row[0]}" if row else "أول تفاعل لهذا المتابع."

                # جلب سياق التغريدة الأصلية
                parent_text = ""
                if t.referenced_tweets:
                    try:
                        parent = client_v2.get_tweet(t.referenced_tweets[0].id).data
                        parent_text = parent.text if parent else ""
                    except: pass

                sys_msg = f"أنت مستشار تقني خليجي رصين. {user_context} رد بلهجة بيضاء، بأسلوب إنساني، وبعمق تقني."
                prompt = f"السياق: {parent_text}\nسؤال المتابع: {t.text}"

                # --- طلب الرد مع Timeout محكم ---
                try:
                    async with httpx.AsyncClient(timeout=20) as client:
                        res = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
                            }
                        )
                        if res.status_code != 200: continue
                        reply_text = res.json()['choices'][0]['message']['content'].strip()
                except Exception as e:
                    logger.error(f"⚠️ خطأ في اتصال AI: {e}")
                    continue

                if is_low_quality(reply_text):
                    logger.warning(f"⚠️ تجاهل رد ركيك لـ {t.id}")
                    continue

                # --- النشر وتحديث الذاكرة ---
                try:
                    client_v2.create_tweet(text=reply_text[:280], in_reply_to_tweet_id=t.id)
                    
                    db.execute("INSERT INTO seen (id) VALUES (?)", (str(t.id),))
                    db.execute("""
                        INSERT INTO user_memory (user_id, last_topic, interaction_count)
                        VALUES (?, ?, 1)
                        ON CONFLICT(user_id) DO UPDATE SET
                        last_topic=excluded.last_topic,
                        interaction_count=interaction_count+1
                    """, (str(t.author_id), summarize_for_memory(t.text)))
                    db.commit()

                    logger.success(f"✅ رد احترافي تم إرساله لـ {t.id}")
                    await asyncio.sleep(2.5) # فاصل زمني لتجنب الـ Rate Limit

                except Exception as e:
                    logger.error(f"❌ فشل نشر التغريدة: {e}")

        except Exception as e:
            logger.error(f"❌ عطل عام في المحرك: {e}")

if __name__ == "__main__":
    asyncio.run(process_mentions())
