import os
import asyncio
import httpx
import tweepy
import re
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

twitter = tweepy.Client(
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🛡️ TEXT REFINER (V45) =================
def refine(text):
    # إزالة الصيني وأي حشو لغوي
    text = re.sub(r'[^\u0600-\u06FF\s\w.,!?;:()@#/-]', '', text)
    # تنظيف المسافات والتأكد من هيبة النص
    return " ".join(text.split())

# ================= 🧠 AI CALL (Advanced Logic) =================
async def ask_ai(system, prompt, temp=0.4):
    async with httpx.AsyncClient(timeout=90) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONF['GROQ']}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": temp,
                "messages": [
                    {"role": "system", "content": system + "\n- اللهجة: خليجية تقنية بيضاء.\n- الشخصية: Senior Tech Lead."},
                    {"role": "user", "content": prompt}
                ]
            }
        )
        return res.json()["choices"][0]["message"]["content"]

# ================= 🔍 TREND DISCOVERY (10x Quality) =================
async def discover_topic():
    system = "أنت رادار تقني يبحث عن 'الفجوات المعرفية' (Knowledge Gaps)."
    prompt = """
اقترح موضوع تقني معقد للأفراد لكنه يغير حياتهم (مثل: الـ Agents الذاتية، قواعد البيانات المحلية، أو أمن الـ AI).
اجعل العنوان 'صادم تقنياً' ومثير للجدل الإيجابي.
"""
    return await ask_ai(system, prompt, temp=0.7)

# ================= 🔬 RESEARCH & KNOWLEDGE =================
async def research(topic):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": CONF["TAVILY"], "query": topic, "search_depth": "advanced"}
        )
        results = res.json().get("results", [])
        return "\n".join(f"- {r['title']}: {r['content']}" for r in results)

async def extract_knowledge(research_data):
    system = "أنت مهندس استخلاص معرفة (Knowledge Engineer)."
    prompt = f"حلل البيانات التالية واستخرج منها الـ (Architecture) والـ (Tools) والـ (Action Plan):\n{research_data}"
    return await ask_ai(system, prompt)

# ================= 🧵 THREAD GENERATION (Masterclass) =================
async def generate_thread(topic, knowledge):
    system = "أنت صانع محتوى تقني (Ghostwriter) لأكبر حسابات التقنية في العالم."
    prompt = f"""
اكتب ثريد (Thread) من 5-6 تغريدات عن: {topic}
المعلومات: {knowledge}

الشروط:
1. التغريدة 1: (The Hook) ابدأ بمشكلة مؤلمة يحلها هذا التقدم التقني.
2. التغريدات 2-4: (The Meat) اشرح الـ Workflow التقني باستخدام مصطلحات (Architecture, Latency, Scalability).
3. التغريدة 5: (The Tools) اذكر الأدوات المحددة وكيف يبدأ الشخص فوراً.
4. التغريدة 6: (The Future) توقع لمستقبل هذه التقنية + سؤال تفاعلي.

* استخدم المصطلحات الإنجليزية بين قوسين بكثافة.
* ممنوع المقدمات المملة.
"""
    raw_thread = await ask_ai(system, prompt, temp=0.6)
    # تنظيف كل تغريدة على حدة
    tweets = [refine(t) for t in raw_thread.split("\n\n") if len(t) > 10]
    return tweets

# ================= 🚀 POST THREAD =================
def post_thread(tweets):
    prev_id = None
    for i, tweet in enumerate(tweets):
        try:
            # إضافة رقم التغريدة للثريد
            text = f"{i+1}/ {tweet}"
            if prev_id is None:
                res = twitter.create_tweet(text=text)
            else:
                res = twitter.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
            prev_id = res.data["id"]
            logger.info(f"Published tweet {i+1}")
            asyncio.sleep(2) # تأخير بسيط لتجنب الـ Rate Limit
        except Exception as e:
            logger.error(f"Error posting tweet {i+1}: {e}")

# ================= 🏁 MAIN =================
async def main():
    logger.info("🚀 AI Content Engine V45 - 10x Quality Mode")
    
    topic = await discover_topic()
    logger.info(f"🎯 Topic Selected: {topic}")

    data = await research(topic)
    knowledge = await extract_knowledge(data)
    
    thread_tweets = await generate_thread(topic, knowledge)
    
    if thread_tweets:
        post_thread(thread_tweets)
        logger.success("🔥 10x Quality Thread is Live!")

if __name__ == "__main__":
    asyncio.run(main())
