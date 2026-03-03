import os
import asyncio
import httpx
import tweepy
import sqlite3
import random
from datetime import datetime, timedelta, timezone
from loguru import logger

# --- 🔐 CONFIG ---
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET"),
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

# --- 🗂 DATABASE ---
db = sqlite3.connect("memory.db")
db.execute("""
CREATE TABLE IF NOT EXISTS seen (
    id TEXT PRIMARY KEY,
    replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS user_memory (
    user_id TEXT,
    last_topic TEXT,
    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# --- 🎭 MOOD ENGINE ---
MOODS = ["ودود مختصر", "تحليلي عميق", "عملي مباشر", "مبسّط جداً"]

def pick_mood():
    hour = datetime.now().hour
    if 0 <= hour <= 6:
        return "مختصر هادئ"
    return random.choice(MOODS)

# --- 🛡 CONTROVERSY GUARD ---
def is_sensitive(text):
    sensitive_keywords = ["سياسة", "طائفية", "هجوم", "فضيحة"]
    return any(word in text for word in sensitive_keywords)

# --- 🧠 BRAIN ---
async def ask_brain(prompt, system_msg):
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(e)
    return None

# --- 🎯 ENGAGEMENT BOOST ---
def enhance_engagement(text):
    if random.random() < 0.3:
        return text + "\n\nوش رأيك أنت؟"
    return text

# --- 🧹 HUMANIZER ---
def humanize(text):
    banned = ["سؤال رائع جداً", "تحليل مذهل"]
    for b in banned:
        text = text.replace(b, "سؤال جميل")
    if random.random() < 0.2:
        parts = text.split(". ")
        if len(parts) > 1:
            text = ". ".join(parts[1:])
    return text.strip()

# --- 💬 MAIN ENGINE ---
async def process_mentions():
    logger.info("🚀 تشغيل النظام المتكامل...")

    try:
        me = client_v2.get_me().data
        mentions = client_v2.get_users_mentions(
            id=me.id,
            tweet_fields=['created_at', 'referenced_tweets', 'author_id'],
            max_results=50
        ).data

        if not mentions:
            return

        time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        for t in mentions:

            if t.created_at < time_threshold:
                continue

            if db.execute("SELECT 1 FROM seen WHERE id=?", (str(t.id),)).fetchone():
                continue

            if is_sensitive(t.text):
                reply_text = "الموضوع هذا يحتاج نقاش أوسع وهدوء أكثر 🙏"
            else:
                parent_text = ""
                if t.referenced_tweets:
                    try:
                        parent = client_v2.get_tweet(
                            t.referenced_tweets[0].id
                        ).data
                        parent_text = parent.text if parent else ""
                    except:
                        pass

                mood = pick_mood()

                sys_msg = f"""
أنت مستشار تقني خليجي إنسان.
مزاجك الحالي: {mood}

- لهجة بيضاء رصينة.
- لا تكرر نفس البداية.
- أضف لمسة إنسانية.
- لا تذكر أسماء.
"""

                prompt = f"السياق: {parent_text}\nالسؤال: {t.text}"

                reply_text = await ask_brain(prompt, sys_msg)

                if reply_text:
                    reply_text = humanize(reply_text)
                    reply_text = enhance_engagement(reply_text)

            if reply_text:
                try:
                    client_v2.create_tweet(
                        text=reply_text[:280],
                        in_reply_to_tweet_id=t.id
                    )

                    db.execute(
                        "INSERT INTO seen (id) VALUES (?)",
                        (str(t.id),)
                    )

                    db.execute(
                        "INSERT INTO user_memory (user_id, last_topic) VALUES (?, ?)",
                        (str(t.author_id), t.text[:100])
                    )

                    db.commit()

                    logger.success(f"✅ رد احترافي على {t.id}")
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(e)

    except Exception as e:
        logger.error(f"❌ عطل عام: {e}")

if __name__ == "__main__":
    asyncio.run(process_mentions())
