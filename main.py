import os
import asyncio
import sqlite3
import hashlib
import statistics
import time
from datetime import datetime, timedelta
import httpx
from quart import Quart, request, jsonify

# ==========================================================
# CONFIG & SECRETS
# ==========================================================
PORT = int(os.getenv("PORT", 8443))
GEMINI_KEY = os.getenv("GEMINI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DATABASE = "data/apex.db"

os.makedirs("data", exist_ok=True)
app = Quart(__name__)

# معرف البوت (يتم استخراجه من التوكن لمنع الرد على النفس)
BOT_ID = TG_TOKEN.split(':')[0] if TG_TOKEN else None
last_interaction = {} # لمنع السبام (Cooldown)

# ==========================================================
# DATABASE INIT
# ==========================================================
conn = sqlite3.connect(DATABASE, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS brain_metrics(brain TEXT PRIMARY KEY, success INTEGER, fail INTEGER, avg_latency REAL, last_updated TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS content_history(hash TEXT PRIMARY KEY, channel TEXT, date TEXT)")
conn.commit()

# ==========================================================
# DIVERSE TOPICS (2026 Focus)
# ==========================================================
TOPICS = [
    "سر مخفي في AI الجوال (Galaxy S26/iPhone 17)",
    "خبايا on-device AI للخصوصية",
    "أسرار نظارات Apple Vision Pro الجديدة",
    "تطبيقات Agentic AI التي تعمل بدلاً منك",
    "خبايا البطاريات وشحن AI الذكي"
]

BRAND_PROFILE = {
    "prompt_base": "أنت أيبكس، خبير تقني خليجي مطلع. تخصصك Artificial Intelligence and its latest tools. لهجتك خليجية بيضاء، مختصرة، وممتعة.",
    "forbidden": ["Industrial Revolution"],
    "hashtags": "#أيبكس_تقني #AI_Secrets #2026"
}

# ==========================================================
# BRAIN & GENERATION ENGINE
# ==========================================================
brain_health = {
    "GEMINI": {"success": 1, "fail": 0, "latency": [], "disabled_until": None},
    "OPENAI": {"success": 1, "fail": 0, "latency": [], "disabled_until": None},
}

async def call_brain(brain, prompt):
    start = time.time()
    try:
        if brain == "GEMINI":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(url, json={"contents":[{"parts":[{"text":prompt}]}]})
                result = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(url, headers=headers, json={
                    "model": "gpt-4o-mini",
                    "messages":[{"role":"user","content":prompt}]
                })
                result = r.json()["choices"][0]["message"]["content"]
        
        latency = time.time() - start
        # تحديث الصحة (Metrics)
        brain_health[brain]["success"] += 1
        brain_health[brain]["latency"].append(latency)
        return result.strip()
    except:
        brain_health[brain]["fail"] += 1
        return None

async def sovereign_generate(mode, context=""):
    # اختيار الدماغ الأفضل (Logic موجود في كودك الأصلي)
    brain = "GEMINI" if brain_health["GEMINI"]["success"] >= brain_health["OPENAI"]["success"] else "OPENAI"
    
    if mode == "POST":
        prompt = f"{BRAND_PROFILE['prompt_base']}\nاكتب سر تقني عن {context}. أضف تحدي يومي وهاشتاجات: {BRAND_PROFILE['hashtags']}"
    else:
        prompt = f"{BRAND_PROFILE['prompt_base']}\nرد بذكاء وبجملة واحدة على: {context}"
        
    return await call_brain(brain, prompt)

# ==========================================================
# WEBHOOK & TARGETED REPLIES
# ==========================================================
@app.route("/webhook", methods=["POST"])
async def webhook():
    data = await request.get_json()
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        user_id = str(msg["from"]["id"])
        
        # 1. منع الرد على النفس أو البوتات
        if user_id == BOT_ID or msg["from"].get("is_bot"):
            return "OK", 200
            
        # 2. فاصل زمني (Cooldown 30 ثانية)
        now = time.time()
        if last_interaction.get(user_id, 0) + 30 > now:
            return "OK", 200
        last_interaction[user_id] = now

        # 3. رد استهدافي ذكي
        reply = await sovereign_generate("REPLY", msg["text"])
        if reply:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(url, json={
                    "chat_id": msg["chat"]["id"],
                    "text": reply,
                    "reply_to_message_id": msg["message_id"]
                })
    return "OK", 200

# ==========================================================
# SCHEDULER (Daily Post)
# ==========================================================
async def scheduler():
    while True:
        # النشر الساعة 9 صباحاً
        if datetime.utcnow().hour == 9:
            topic = random.choice(TOPICS)
            content = await sovereign_generate("POST", topic)
            if content:
                h = hashlib.sha256(content.encode()).hexdigest()
                exists = conn.execute("SELECT 1 FROM content_history WHERE hash=?", (h,)).fetchone()
                
                if not exists:
                    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                    async with httpx.AsyncClient() as client:
                        await client.post(url, json={
                            "chat_id": TG_CHAT_ID,
                            "text": f"<b>🌟 سر أيبكس اليومي</b>\n\n{content}",
                            "parse_mode": "HTML"
                        })
                    conn.execute("INSERT INTO content_history VALUES (?, ?, ?)", (h, "TG", datetime.utcnow().isoformat()))
                    conn.commit()
            await asyncio.sleep(3601) # منع تكرار النشر في نفس الساعة
        await asyncio.sleep(600)

@app.before_serving
async def startup():
    asyncio.create_task(scheduler())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
